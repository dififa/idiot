import argparse
import yfinance as yf
import pandas as pd

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Download emiten data dari Yahoo Finance.")
    parser.add_argument(
        "ticker",
        nargs="?",
        default="BRPT",
        help="Ticker emiten tunggal (default: BRPT).",
    )
    parser.add_argument(
        "--period",
        type=str,
        default="1mo",
        help="Periode data misal: 1d, 5d, 1mo, 1y (default: 1mo)",
    )
    
    args = parser.parse_args()

    # Normalisasi ticker
    clean_ticker = args.ticker.strip().upper()
    if clean_ticker.endswith(".JK"):
        clean_ticker = clean_ticker[:-3]

    ticker = f"{clean_ticker}.JK"
    emiten = yf.Ticker(ticker)
    
    df = emiten.history(period=args.period)
    
    # --- FALLBACK LOGIC ---
    # Tarik juga data 1 hari terakhir buat jaga-jaga kalau tanggal terbaru belum masuk
    df_1d = emiten.history(period="1d")
    
    if not df_1d.empty:
        # Gabungin data period dengan data 1d
        df = pd.concat([df, df_1d])
        # Buang duplikat berdasarkan index (tanggal), keep='last' biar dapet update harga terbaru
        df = df[~df.index.duplicated(keep='last')]
        # Pastiin urutannya dari tanggal terlama ke terbaru lagi buat hitungan rumus di bawah
        df = df.sort_index()
    # ----------------------

    if df.empty:
        print(f"Yah, data tidak ditemukan untuk ticker {args.ticker} nih kak.")
        return

    # Reset index agar Date menjadi kolom
    df = df.reset_index()

    # Hitung PrevClose (Close hari sebelumnya), Daily Return, dan GapToHigh
    # Harus dihitung sebelum disortir descending
    df['PrevClose'] = df['Close'].shift(1)
    df['Return'] = ((df['Close'] - df['PrevClose']) / df['PrevClose']) * 100
    df['GapHigh'] = ((df['High'] - df['PrevClose']) / df['PrevClose']) * 100

    # Sortir berdasarkan tanggal terbaru (descending)
    df = df.sort_values(by='Date', ascending=False)

    # Format kolom Date agar rapi (menghilangkan timezone)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

    # Filter dan susun kolom sesuai permintaan
    columns_to_show = ['Date', 'Open', 'Low', 'High', 'Close', 'Return', 'GapHigh']
    result = df[columns_to_show].copy()

    # Format angka desimal agar lebih mudah dibaca
    for col in ['Open', 'Low', 'High', 'Close']:
        result[col] = result[col].apply(lambda x: f"{x:.0f}" if pd.notnull(x) else " ")
    
    # Format Return dan GapToHigh menjadi persentase
    result['Return'] = result['Return'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else " ")
    result['GapHigh'] = result['GapHigh'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else " ")

    # Cetak hasil dengan warna text: merah untuk < 0, hijau untuk >= 0
    table_lines = result.to_string(index=False).splitlines()

    COLOR_RED = "\033[91m"
    COLOR_GREEN = "\033[92m"
    RESET = "\033[0m"

    # Hitung Pivot Support S1 & S2 dari data hari terakhir
    latest = df.iloc[0]
    high = float(latest['High'])
    low = float(latest['Low'])
    close = float(latest['Close'])

    pp = (high + low + close) / 3.0
    s1 = (2.0 * pp) - high
    s2 = pp - (high - low)

    print(f"TABEL {args.period.upper()} {ticker}")
    print(f"S1\t: {s1:.0f}")
    print(f"S2\t: {s2:.0f}")
    print(table_lines[0])  # Header
    for i, line in enumerate(table_lines[1:]):
        ret_val = df['Return'].iloc[i]
        formatted_ret = result['Return'].iloc[i]
        formatted_gth = result['GapHigh'].iloc[i]

        if pd.notnull(ret_val) and formatted_ret.strip():
            color = COLOR_RED if ret_val < 0 else COLOR_GREEN
            limit = line.rfind(formatted_gth) if (pd.notnull(df['GapHigh'].iloc[i]) and formatted_gth.strip()) else len(line)
            idx = line.rfind(formatted_ret, 0, limit if limit != -1 else len(line))
            if idx != -1:
                line = line[:idx] + f"{color}{formatted_ret}{RESET}" + line[idx + len(formatted_ret):]

        print(line)


if __name__ == "__main__":
    main()
