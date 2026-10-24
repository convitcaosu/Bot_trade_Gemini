//+------------------------------------------------------------------+
//|                                          GeminiTickCollector.mq5 |
//|  V4 tick + candle collector for Gemini Trade Bot Pro               |
//|  Host chart: attach to XAUUSD (any chart works as host).           |
//|  The host chart does NOT limit the scan: this EA loops over        |
//|  symbols from Market Watch (or InpSymbols) and exports:            |
//|   1. Historical ticks, old -> new, chunked by day (CopyTicksRange) |
//|   2. Historical candles M5/M15/H1/H4 for V4 HTF context            |
//|   3. Realtime ticks while the market is open (OnTimer polling,     |
//|      because OnTick only fires for the host chart symbol)          |
//|  Output: <Terminal>/MQL5/Files/gemini_ticks/                       |
//|    ticks_<SYMBOL>_YYYYMMDD.csv  (time_ms,bid,ask,last,volume,flags)|
//|    candles_<SYMBOL>_<TF>.csv    (time,open,high,low,close,volume)  |
//|    collector_status.txt         (progress, last tick time)         |
//|  NOTE: tick history depth is limited by the broker server (Exness |
//|  typically keeps days/weeks of ticks, not years). A day with no    |
//|  server data is skipped, not faked. Files can be large: XAUUSD    |
//|  produces millions of ticks per day — keep InpMaxDays small first. |
//+------------------------------------------------------------------+
#property copyright "Gemini Trade Bot Pro V4"
#property version   "4.00"
#property strict

input string   InpSymbols      = "";      // "" = all visible Market Watch symbols
input int      InpMaxDays      = 7;       // historical tick days, old -> new
input int      InpTimerSec     = 1;       // realtime poll interval (seconds)
input bool     InpExportCandles= true;    // also export M5/M15/H1/H4 candles
input int      InpCandleCount  = 5000;    // candles per symbol/TF
input string   InpOutFolder    = "gemini_ticks";

string g_symbols[];
datetime g_last_tick_time[];
bool g_history_done = false;
int g_hist_index = 0;

//--- helpers
string TFName(ENUM_TIMEFRAMES tf)
{
   if(tf==PERIOD_M5)  return "M5";
   if(tf==PERIOD_M15) return "M15";
   if(tf==PERIOD_H1)  return "H1";
   if(tf==PERIOD_H4)  return "H4";
   return EnumToString(tf);
}

int CollectSymbols()
{
   ArrayResize(g_symbols, 0);
   if(StringLen(InpSymbols) > 0)
   {
      ushort sep = StringGetCharacter(",", 0);
      string parts[];
      int n = StringSplit(InpSymbols, sep, parts);
      for(int i=0; i<n; i++)
      {
         string s = parts[i];
         StringTrimLeft(s); StringTrimRight(s);
         if(StringLen(s) > 0)
         {
            int sz = ArraySize(g_symbols);
            ArrayResize(g_symbols, sz+1);
            g_symbols[sz] = s;
         }
      }
   }
   else
   {
      int total = SymbolsTotal(true); // visible only
      for(int i=0; i<total; i++)
      {
         string s = SymbolName(i, true);
         int sz = ArraySize(g_symbols);
         ArrayResize(g_symbols, sz+1);
         g_symbols[sz] = s;
      }
   }
   ArrayResize(g_last_tick_time, ArraySize(g_symbols));
   for(int i=0; i<ArraySize(g_last_tick_time); i++)
      g_last_tick_time[i] = 0;
   return ArraySize(g_symbols);
}

void WriteStatus(string msg)
{
   int h = FileOpen(InpOutFolder + "\\collector_status.txt", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      FileWriteString(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " | " + msg + "\n");
      FileClose(h);
   }
   Comment("GEMINI TICK COLLECTOR v4\n" + msg);
}

void ExportCandlesFor(string sym)
{
   ENUM_TIMEFRAMES tfs[4] = {PERIOD_M5, PERIOD_M15, PERIOD_H1, PERIOD_H4};
   for(int t=0; t<4; t++)
   {
      MqlRates rates[];
      int copied = CopyRates(sym, tfs[t], 0, InpCandleCount, rates);
      if(copied <= 0) continue;
      string fn = InpOutFolder + "\\candles_" + sym + "_" + TFName(tfs[t]) + ".csv";
      int h = FileOpen(fn, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
      if(h == INVALID_HANDLE) continue;
      FileWrite(h, "time", "open", "high", "low", "close", "volume");
      for(int i=0; i<copied; i++)
         FileWrite(h, TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS),
                   DoubleToString(rates[i].open, _Digits),
                   DoubleToString(rates[i].high, _Digits),
                   DoubleToString(rates[i].low, _Digits),
                   DoubleToString(rates[i].close, _Digits),
                   IntegerToString(rates[i].tick_volume));
      FileClose(h);
   }
}

void ExportTicksDay(string sym, int sym_index, datetime day_start)
{
   datetime day_end = day_start + 86400 - 1;
   MqlTick ticks[];
   int copied = CopyTicksRange(sym, ticks, COPY_TICKS_ALL, (ulong)day_start*1000, (ulong)day_end*1000);
   if(copied <= 0) return; // no server data for this day: skip, do not fake
   string datestr = TimeToString(day_start, TIME_DATE);
   StringReplace(datestr, ".", "");
   string fn = InpOutFolder + "\\ticks_" + sym + "_" + datestr + ".csv";
   int h = FileOpen(fn, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   FileWrite(h, "time_ms", "bid", "ask", "last", "volume", "flags");
   for(int i=0; i<copied; i++)
      FileWrite(h, IntegerToString(ticks[i].time_msc),
                DoubleToString(ticks[i].bid, _Digits),
                DoubleToString(ticks[i].ask, _Digits),
                DoubleToString(ticks[i].last, _Digits),
                IntegerToString(ticks[i].volume),
                IntegerToString(ticks[i].flags));
   FileClose(h);
   if(copied > 0 && sym_index >= 0 && sym_index < ArraySize(g_last_tick_time))
      g_last_tick_time[sym_index] = ticks[copied-1].time;
}

int OnInit()
{
   int n = CollectSymbols();
   if(n <= 0)
   {
      Print("GeminiTickCollector: no symbols found. Add symbols to Market Watch.");
      return INIT_FAILED;
   }
   FolderCreate(InpOutFolder);
   EventSetTimer(InpTimerSec);
   WriteStatus("Init OK. Symbols: " + IntegerToString(n) + " | host: " + _Symbol +
               " | history days: " + IntegerToString(InpMaxDays));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTick()
{
   // OnTick only fires for the host chart symbol. Realtime for ALL symbols
   // is handled in OnTimer below; this keeps the host tick path alive.
   ProcessRealtime();
}

void OnTimer()
{
   // 1) Historical export, one symbol per timer tick, old -> new.
   //    Chunked by day so the terminal never freezes on millions of ticks.
   if(!g_history_done)
   {
      if(g_hist_index < ArraySize(g_symbols))
      {
         string sym = g_symbols[g_hist_index];
         SymbolSelect(sym, true);
         datetime now = TimeCurrent();
         datetime start_day = (now - InpMaxDays*86400);
         // align to day start (server time)
         MqlDateTime dt; TimeToStruct(start_day, dt);
         dt.hour = 0; dt.min = 0; dt.sec = 0;
         start_day = StructToTime(dt);
         for(datetime d = start_day; d < now; d += 86400)
            ExportTicksDay(sym, g_hist_index, d);
         if(InpExportCandles) ExportCandlesFor(sym);
         g_hist_index++;
         WriteStatus("History " + IntegerToString(g_hist_index) + "/" +
                     IntegerToString(ArraySize(g_symbols)) + " done: " + sym);
         if(g_hist_index >= ArraySize(g_symbols))
         {
            g_history_done = true;
            WriteStatus("History complete. Now realtime only.");
         }
      }
      return;
   }
   // 2) Realtime after history is done.
   ProcessRealtime();
}

void ProcessRealtime()
{
   for(int i=0; i<ArraySize(g_symbols); i++)
   {
      string sym = g_symbols[i];
      MqlTick ticks[];
      ulong from_msc = (ulong)g_last_tick_time[i]*1000;
      int copied;
      if(from_msc == 0)
         copied = CopyTicks(sym, ticks, COPY_TICKS_ALL, 0, 1000);
      else
         copied = CopyTicksRange(sym, ticks, COPY_TICKS_ALL, from_msc+1, (ulong)TimeCurrent()*1000 + 60000);
      if(copied <= 0) continue;
      // append to today's file
      MqlDateTime dt; TimeToStruct(ticks[0].time, dt);
      string datestr = StringFormat("%04d%02d%02d", dt.year, dt.mon, dt.day);
      string fn = InpOutFolder + "\\ticks_" + sym + "_" + datestr + ".csv";
      bool exists = FileIsExist(fn);
      int h = FileOpen(fn, FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI, ',');
      if(h == INVALID_HANDLE) continue;
      if(!exists)
         FileWrite(h, "time_ms", "bid", "ask", "last", "volume", "flags");
      else
         FileSeek(h, 0, SEEK_END);
      for(int j=0; j<copied; j++)
         FileWrite(h, IntegerToString(ticks[j].time_msc),
                   DoubleToString(ticks[j].bid, _Digits),
                   DoubleToString(ticks[j].ask, _Digits),
                   DoubleToString(ticks[j].last, _Digits),
                   IntegerToString(ticks[j].volume),
                   IntegerToString(ticks[j].flags));
      FileClose(h);
      g_last_tick_time[i] = ticks[copied-1].time;
   }
}
//+------------------------------------------------------------------+
