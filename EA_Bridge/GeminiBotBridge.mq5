//+------------------------------------------------------------------+
//|                                           GeminiBotBridge.mq5    |
//|            EA CẦU NỐI — Gemini Trade Bot Pro v3.0                |
//|  Chức năng:                                                      |
//|  1. Tự động nhận diện symbol & timeframe (XAUUSD, Cent, Forex...) |
//|  2. Dynamic SL/TP: TP1 (bảo toàn), TP2 (mục tiêu), TP3 (tham vọng) |
//|  3. Xuất 15.000 nến (2 tháng) cho Python phân tích & Backtest    |
//|  4. Tự động chụp chart nét căng khi phát hiện setup              |
//|  5. Bắn tín hiệu song song qua Desktop App & Telegram           |
//+------------------------------------------------------------------+
#property copyright "Gemini Trade Bot Pro v3.0"
#property link      "https://ai.google.dev"
#property version   "3.00"
#property strict
#property description "EA cầu nối MT5 và Gemini Trade Bot Pro v3.0 - Dynamic SL/TP & Backtest 2 Tháng"

//--- Input Parameters
input string   InpOutputPath        = "";           // Thư mục mt5_signals (để trống = tự detect)
input int      InpSwingLookback     = 20;           // Số nến quét swing high/low
input double   InpMinWickPct        = 55.0;         // % râu nến tối thiểu (Pin Bar)
input bool     InpAutoScreenshot    = true;         // Tự chụp chart khi có setup
input bool     InpWriteSignalFile   = true;         // Ghi file .signal để bot đọc
input bool     InpAutoExportHistory = true;         // Tự xuất 2 tháng nến khi gắn vào chart
input int      InpCheckInterval     = 3;            // Kiểm tra mỗi N giây
input color    InpBuyColor          = clrLimeGreen; // Màu BUY trên chart
input color    InpSellColor         = clrOrangeRed; // Màu SELL trên chart

//--- Biến toàn cục
string   g_output_path = "";
datetime g_last_bar_time = 0;
datetime g_last_signal_time = 0;
int      g_signal_count = 0;
string   g_btn_backtest_name = "GBOT_Btn_Backtest";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Xác định đường dẫn output
   if(InpOutputPath != "")
   {
      g_output_path = InpOutputPath;
   }
   else
   {
      g_output_path = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\mt5_signals";
   }
   
   // Tạo thư mục nếu chưa có
   FolderCreate("mt5_signals", FILE_COMMON);
   FolderCreate("mt5_signals", 0);
   
   Print("════════════════════════════════════════════════════════════");
   Print("⚡ GEMINI BOT BRIDGE v3.0 — Khởi động thành công!");
   Print("📊 Symbol Hiện Tại: ", _Symbol, " | TF: ", EnumToString((ENUM_TIMEFRAMES)_Period));
   Print("📁 Thư mục tín hiệu: ", g_output_path);
   Print("════════════════════════════════════════════════════════════");
   
   // Ghi nhận symbol hiện tại để Desktop App tự nhận diện ngay
   SaveCurrentSymbolInfo();
   
   // Vẽ giao diện điều khiển trên chart
   DrawStatusLabel("⚡ GEMINI BOT BRIDGE v3.0 — RUNNING | " + _Symbol, clrAqua);
   CreateBacktestButton();
   
   // Tự động xuất 2 tháng lịch sử nến nếu được bật
   if(InpAutoExportHistory)
   {
      ExportHistoricalCandles(15000);
   }
   
   // Timer để kiểm tra liên tục
   EventSetTimer(InpCheckInterval);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, "GBOT_");
   Print("🛑 Gemini Bot Bridge — Đã dừng.");
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   CheckNewBar();
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   CheckNewBar();
}

//+------------------------------------------------------------------+
//| Chart Event — Bắt sự kiện bấm nút trên chart                     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK)
   {
      if(sparam == g_btn_backtest_name)
      {
         Print("⚡ Trader bấm nút QUÉT 2 THÁNG trên chart...");
         DrawStatusLabel("⏳ Đang xuất 15.000 nến cho Bot...", clrYellow);
         ExportHistoricalCandles(15000);
         DrawStatusLabel("✅ Đã xuất xong 15.000 nến! Mở App xem Backtest", clrLimeGreen);
         ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_STATE, false);
         ChartRedraw(0);
      }
   }
}

//+------------------------------------------------------------------+
//| Ghi thông tin symbol hiện tại vào file                           |
//+------------------------------------------------------------------+
void SaveCurrentSymbolInfo()
{
   int handle = FileOpen("mt5_signals\\current_symbol.txt", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle != INVALID_HANDLE)
   {
      FileWriteString(handle, "symbol=" + _Symbol + "\n");
      FileWriteString(handle, "timeframe=" + EnumToString((ENUM_TIMEFRAMES)_Period) + "\n");
      FileWriteString(handle, "digits=" + IntegerToString(_Digits) + "\n");
      FileWriteString(handle, "point=" + DoubleToString(_Point, _Digits) + "\n");
      FileWriteString(handle, "timestamp=" + TimeToString(TimeCurrent()) + "\n");
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
//| Xuất N nến lịch sử ra CSV để Python phân tích Backtest           |
//+------------------------------------------------------------------+
void ExportHistoricalCandles(int count=15000)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, _Period, 0, count, rates);
   if(copied <= 0)
   {
      Print("❌ Không lấy được nến lịch sử cho ", _Symbol);
      return;
   }
   
   string filename = "mt5_signals\\history_" + _Symbol + ".csv";
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("❌ Không mở được file: ", filename);
      return;
   }
   
   FileWriteString(handle, "timestamp,open,high,low,close,volume\n");
   for(int i = copied - 1; i >= 0; i--)
   {
      string line = TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES) + "," +
                    DoubleToString(rates[i].open, _Digits) + "," +
                    DoubleToString(rates[i].high, _Digits) + "," +
                    DoubleToString(rates[i].low, _Digits) + "," +
                    DoubleToString(rates[i].close, _Digits) + "," +
                    IntegerToString(rates[i].tick_volume) + "\n";
      FileWriteString(handle, line);
   }
   FileClose(handle);
   Print("✅ Đã xuất ", copied, " nến lịch sử ra: ", filename);
}

//+------------------------------------------------------------------+
//| Kiểm tra nến mới đóng                                            |
//+------------------------------------------------------------------+
void CheckNewBar()
{
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time == g_last_bar_time)
      return;
   
   g_last_bar_time = current_bar_time;
   AnalyzeLastCandle();
}

//+------------------------------------------------------------------+
//| Phân tích nến vừa đóng — Dynamic SL/TP linh động                 |
//+------------------------------------------------------------------+
void AnalyzeLastCandle()
{
   int total_bars = InpSwingLookback + 10;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, _Period, 0, total_bars, rates);
   if(copied < total_bars) return;
   
   double open1   = rates[1].open;
   double high1   = rates[1].high;
   double low1    = rates[1].low;
   double close1  = rates[1].close;
   double range1  = high1 - low1;
   if(range1 <= 0) return;
   
   double lowest_low   = DBL_MAX;
   double highest_high  = -DBL_MAX;
   for(int i = 2; i < InpSwingLookback + 2; i++)
   {
      if(rates[i].low < lowest_low) lowest_low = rates[i].low;
      if(rates[i].high > highest_high) highest_high = rates[i].high;
   }
   
   // ═══ CHECK BUY SETUP (Liquidity Sweep Đáy + Bullish Pinbar) ═══
   bool is_buy_swept  = (low1 < lowest_low) && (close1 > lowest_low);
   double lower_wick  = MathMin(open1, close1) - low1;
   double buy_wick_pct = (lower_wick / range1) * 100.0;
   bool is_buy_pin    = (close1 >= open1) && (buy_wick_pct >= InpMinWickPct);
   
   // ═══ CHECK SELL SETUP (Liquidity Sweep Đỉnh + Bearish Pinbar) ═══
   bool is_sell_swept  = (high1 > highest_high) && (close1 < highest_high);
   double upper_wick   = high1 - MathMax(open1, close1);
   double sell_wick_pct = (upper_wick / range1) * 100.0;
   bool is_sell_pin    = (close1 <= open1) && (sell_wick_pct >= InpMinWickPct);
   
   string direction = "";
   double wick_pct  = 0;
   double sweep_pips = 0;
   double entry = close1;
   double sl = 0, tp1 = 0, tp2 = 0, tp3 = 0;
   double risk = 0;
   
   if(is_buy_swept && is_buy_pin)
   {
      direction  = "BUY";
      wick_pct   = buy_wick_pct;
      sweep_pips = MathAbs(lowest_low - low1) / _Point;
      sl         = low1 - (range1 * 0.20);
      risk       = entry - sl;
      if(risk <= 0) return;
      
      // Dynamic SL/TP linh động:
      tp1 = entry + (risk * 1.5); // TP1 bảo toàn (chốt 40% + dời breakeven)
      tp2 = entry + (risk * 2.8); // TP2 mục tiêu chính (chốt 40%)
      tp3 = entry + (risk * 4.5); // TP3 tham vọng (trailing 20%)
   }
   else if(is_sell_swept && is_sell_pin)
   {
      direction  = "SELL";
      wick_pct   = sell_wick_pct;
      sweep_pips = MathAbs(high1 - highest_high) / _Point;
      sl         = high1 + (range1 * 0.20);
      risk       = sl - entry;
      if(risk <= 0) return;
      
      tp1 = entry - (risk * 1.5);
      tp2 = entry - (risk * 2.8);
      tp3 = entry - (risk * 4.5);
   }
   else
   {
      return;
   }
   
   // Tránh spam
   if(TimeCurrent() - g_last_signal_time < 60) return;
   g_last_signal_time = TimeCurrent();
   g_signal_count++;
   
   string session = GetSession(TimeHour(rates[1].time));
   
   Print("═══════════════════════════════════════════════════");
   Print("🎯 SETUP PHÁT HIỆN #", g_signal_count, " [", direction, " ", _Symbol, "]");
   Print("💰 Entry: ", DoubleToString(entry, _Digits));
   Print("🛑 SL: ", DoubleToString(sl, _Digits));
   Print("🥇 TP1 (Bảo toàn): ", DoubleToString(tp1, _Digits));
   Print("🥈 TP2 (Mục tiêu): ", DoubleToString(tp2, _Digits));
   Print("🥉 TP3 (Tham vọng): ", DoubleToString(tp3, _Digits));
   Print("═══════════════════════════════════════════════════");
   
   // Vẽ các mốc TP1, TP2, TP3 lên chart
   DrawSignalLines(direction, entry, sl, tp1, tp2, tp3);
   
   if(InpAutoScreenshot)
      TakeScreenshot(direction, wick_pct);
   
   if(InpWriteSignalFile)
      WriteSignalFile(direction, entry, sl, tp1, tp2, tp3, wick_pct, sweep_pips, session);
   
   Alert("⚡ GEMINI BOT v3.0: ", direction, " ", _Symbol, " | Entry: ", 
         DoubleToString(entry, _Digits), " | Wick: ", DoubleToString(wick_pct, 1), "%");
}

//+------------------------------------------------------------------+
//| Chụp ảnh chart nét                                               |
//+------------------------------------------------------------------+
void TakeScreenshot(string direction, double wick_pct)
{
   string filename = _Symbol + "_" + EnumToString((ENUM_TIMEFRAMES)_Period) + "_" 
                     + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   StringReplace(filename, ":", "");
   StringReplace(filename, " ", "_");
   StringReplace(filename, ".", "");
   
   string full_path = "mt5_signals\\" + filename + ".png";
   ChartScreenShot(0, full_path, 1920, 1080, ALIGN_RIGHT);
}

//+------------------------------------------------------------------+
//| Ghi file .signal với Dynamic TP1, TP2, TP3                        |
//+------------------------------------------------------------------+
void WriteSignalFile(string direction, double entry, double sl, double tp1,
                     double tp2, double tp3, double wick_pct, double sweep_pips, string session)
{
   string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   StringReplace(timestamp, ":", "");
   StringReplace(timestamp, " ", "_");
   
   string filename = "mt5_signals\\" + _Symbol + "_" + timestamp + ".signal";
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE) return;
   
   FileWriteString(handle, "symbol=" + _Symbol + "\n");
   FileWriteString(handle, "timeframe=" + EnumToString((ENUM_TIMEFRAMES)_Period) + "\n");
   FileWriteString(handle, "direction=" + direction + "\n");
   FileWriteString(handle, "entry=" + DoubleToString(entry, _Digits) + "\n");
   FileWriteString(handle, "sl=" + DoubleToString(sl, _Digits) + "\n");
   FileWriteString(handle, "tp1=" + DoubleToString(tp1, _Digits) + "\n");
   FileWriteString(handle, "tp2=" + DoubleToString(tp2, _Digits) + "\n");
   FileWriteString(handle, "tp3=" + DoubleToString(tp3, _Digits) + "\n");
   FileWriteString(handle, "tp=" + DoubleToString(tp2, _Digits) + "\n");
   FileWriteString(handle, "wick_pct=" + DoubleToString(wick_pct, 1) + "\n");
   FileWriteString(handle, "sweep_pips=" + DoubleToString(sweep_pips, 1) + "\n");
   FileWriteString(handle, "session=" + session + "\n");
   FileWriteString(handle, "timestamp=" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\n");
   FileClose(handle);
}

//+------------------------------------------------------------------+
//| Xác định phiên                                                   |
//+------------------------------------------------------------------+
string GetSession(int hour)
{
   if(hour >= 0 && hour < 8) return "Asian";
   else if(hour >= 8 && hour < 15) return "London";
   else return "New York";
}

//+------------------------------------------------------------------+
//| Vẽ đường Entry / SL / TP1 / TP2 / TP3 lên chart                  |
//+------------------------------------------------------------------+
void DrawSignalLines(string direction, double entry, double sl, double tp1, double tp2, double tp3)
{
   ObjectsDeleteAll(0, "GBOT_Line_");
   
   // Entry
   CreateHLine("GBOT_Line_Entry", entry, clrDodgerBlue, "ENTRY: " + DoubleToString(entry, _Digits));
   // SL
   CreateHLine("GBOT_Line_SL", sl, clrCrimson, "SL: " + DoubleToString(sl, _Digits));
   // TP1
   CreateHLine("GBOT_Line_TP1", tp1, clrGold, "TP1 (Bảo toàn 40%): " + DoubleToString(tp1, _Digits));
   // TP2
   CreateHLine("GBOT_Line_TP2", tp2, clrLimeGreen, "TP2 (Mục tiêu 40%): " + DoubleToString(tp2, _Digits));
   // TP3
   CreateHLine("GBOT_Line_TP3", tp3, clrDeepSkyBlue, "TP3 (Trailing 20%): " + DoubleToString(tp3, _Digits));
   
   ChartRedraw(0);
}

void CreateHLine(string name, double price, color clr, string desc)
{
   ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
   ObjectSetString(0, name, OBJPROP_TEXT, desc);
}

//+------------------------------------------------------------------+
//| Nút bấm Quét 2 Tháng trực tiếp trên chart                        |
//+------------------------------------------------------------------+
void CreateBacktestButton()
{
   ObjectDelete(0, g_btn_backtest_name);
   ObjectCreate(0, g_btn_backtest_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_YDISTANCE, 60);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_XSIZE, 190);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_YSIZE, 30);
   ObjectSetString(0, g_btn_backtest_name, OBJPROP_TEXT, "⚡ QUÉT 2 THÁNG NẾN");
   ObjectSetString(0, g_btn_backtest_name, OBJPROP_FONT, "Segoe UI");
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_FONTSIZE, 10);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_BGCOLOR, clrRoyalBlue);
   ObjectSetInteger(0, g_btn_backtest_name, OBJPROP_SELECTABLE, false);
}

void DrawStatusLabel(string text, color clr)
{
   string name = "GBOT_Status";
   ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 30);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}
