import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter
import plotly.express as px
import re
import unicodedata

st.set_page_config(page_title="USGEP Branş Yönlendirme", layout="wide")

st.markdown("""
<style>
.main-title{
    font-size:42px;
    font-weight:700;
    color:#0F172A;
    margin-top:20px;
}
.subtitle{
    font-size:18px;
    color:#475569;
    margin-bottom:30px;
}
.metric-card{
    background-color:#F8FAFC;
    padding:25px;
    border-radius:18px;
    border:1px solid #E2E8F0;
    text-align:center;
}
.metric-number{
    font-size:38px;
    font-weight:700;
    color:#2563EB;
}
.metric-label{
    font-size:15px;
    color:#64748B;
}
.stButton>button{
    width:100%;
    height:55px;
    border-radius:14px;
    border:none;
    background-color:#2563EB;
    color:white;
    font-size:18px;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

sol, sag = st.columns([1, 5])

with sol:
    logo_yolu = Path(__file__).parent / "logo.png"
    if logo_yolu.exists():
        st.image(str(logo_yolu), width=220)

with sag:
    st.markdown(
        '<div class="main-title">USGEP Branş Yönlendirme Sistemi</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="subtitle">Ham test verilerini norm tablolarına göre puanlar, branş uygunluklarını hesaplar ve düzenlenmiş Excel çıktısı oluşturur.</div>',
        unsafe_allow_html=True
    )

st.subheader("Dosya Yükleme Alanı")

col1, col2 = st.columns(2)

with col1:
    ham_dosya = st.file_uploader("Ham test Excel dosyasını yükle", type=["xlsx"])

with col2:
    norm_dosya = st.file_uploader("Norm tablo Excel dosyasını yükle", type=["xlsx"])

RENKLER = {
    4: "FF0000",
    8: "FFC000",
    12: "5B9BD5",
    16: "A9D08E",
    20: "00B050",
}

TEST_SAYFA_ESLESME = {
    "BOY": "BOY",
    "KİLO": "KİLO",
    "KULAÇ": "KULAÇ",
    "DURARAK UZUN ATLAMA": "DURARAK UZUN ATLAMA",
    "DİKEY SIÇRAMA": "DİKEY SIÇRAMA",
    "EL KAVRAMA": "EL KAVRAMA",
    "GERİYE SAĞLIK TOPU ATMA": "GERİYE SAĞLIK TOPU FIRLATMA",
    "20 M. SPRINT": "20 M. SPRINT",
    "AYAK ÇABUKLUĞU": "AYAK ÇABUKLUĞU",
    "EL ÇABUKLUĞU": "EL ÇABUKLUĞU",
    "SIRT BACAK": "SIRT BACAK KUVVETİ",
    "HEXAGON": "HEXAGON",
    "LANE AGILITY": "LANE ÇEVİKLİK",
}

TESTLER = list(TEST_SAYFA_ESLESME.keys()) + ["FONKSİYONEL ÇÖMELME"]

CIKTI_TEST_SIRASI = [
    "BOY",
    "KİLO",
    "BACAK BOYU",
    "OTURMA YÜKSEKLİĞİ",
    "BACAK UZUNLUĞU",
    "KULAÇ",
    "FONKSİYONEL ÇÖMELME",
    "EL ÇABUKLUĞU",
    "AYAK ÇABUKLUĞU",
    "EL KAVRAMA",
    "SIRT BACAK",
    "HEXAGON",
    "DURARAK UZUN ATLAMA",
    "GERİYE SAĞLIK TOPU ATMA",
    "DİKEY SIÇRAMA",
    "LANE AGILITY",
    "20 M. SPRINT",
]

BRANS_KRITERLERI = {
    "KARATE": {
        "yas": [7, 8, 9],
        "cinsiyet": ["ERKEK", "KIZ"],
        "kriterler": ["BACAK UZUNLUĞU", "KULAÇ", "DURARAK UZUN ATLAMA", "AYAK ÇABUKLUĞU", "EL ÇABUKLUĞU"],
    },
    "TEKVANDO": {
        "yas": [7, 8, 9],
        "cinsiyet": ["ERKEK", "KIZ"],
        "kriterler": ["BACAK UZUNLUĞU", "KULAÇ", "DURARAK UZUN ATLAMA", "AYAK ÇABUKLUĞU", "FONKSİYONEL ÇÖMELME"],
    },
    "BOKS": {
        "yas": [9, 10, 11],
        "cinsiyet": ["ERKEK", "KIZ"],
        "kriterler": ["KULAÇ", "HEXAGON", "GERİYE SAĞLIK TOPU ATMA", "AYAK ÇABUKLUĞU", "EL ÇABUKLUĞU"],
    },
    "JUDO": {
        "yas": [7, 8, 9, 10, 11],
        "cinsiyet": ["ERKEK", "KIZ"],
        "kriterler": ["DURARAK UZUN ATLAMA", "GERİYE SAĞLIK TOPU ATMA", "SIRT BACAK", "EL KAVRAMA", "AYAK ÇABUKLUĞU"],
    },
    "GÜREŞ": {
        "yas": [9, 10],
        "cinsiyet": ["ERKEK"],
        "kriterler": ["DURARAK UZUN ATLAMA", "GERİYE SAĞLIK TOPU ATMA", "SIRT BACAK", "EL KAVRAMA", "FONKSİYONEL ÇÖMELME"],
    },
}


def normalize_text(x):
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(c for c in x if not unicodedata.combining(c))
    x = x.replace("\n", " ")
    x = re.sub(r"\s+", " ", x)
    return x


def temizle_metin(x):
    return str(x).strip().upper()


def sayiya_cevir(x):
    return float(str(x).replace(",", ".").strip())


def kolon_bul(df, adaylar):
    normalized_cols = {normalize_text(c): c for c in df.columns}

    for aday in adaylar:
        aday_norm = normalize_text(aday)

        for norm_col, original_col in normalized_cols.items():
            if aday_norm in norm_col:
                return original_col

    return None


def aralik_uyuyor_mu(deger, aralik):
    metin = str(aralik).replace(",", ".").strip()
    sayilar = re.findall(r"\d+(?:\.\d+)?", metin)

    if not sayilar:
        return False

    sayilar = [float(s) for s in sayilar]

    if "≤" in metin or "<=" in metin:
        return deger <= sayilar[0]

    if "≥" in metin or ">=" in metin:
        return deger >= sayilar[0]

    if "-" in metin and len(sayilar) >= 2:
        alt = min(sayilar[0], sayilar[1])
        ust = max(sayilar[0], sayilar[1])
        return alt <= deger <= ust

    return False


def fonksiyonel_puanla(deger):
    deger = str(deger).strip()

    if deger == "1":
        return 4
    elif deger == "2":
        return 8
    elif deger == "3":
        return 16
    elif deger == "4":
        return 20

    return 4


def norm_puanla(deger, norm_satiri):
    if pd.isna(deger) or temizle_metin(deger) in ["VERİ YOK", "VERI YOK", "G", "K", "NAN", ""]:
        return 4

    try:
        deger = sayiya_cevir(deger)
    except Exception:
        return 4

    kolon_puanlari = {
        "ÇOK ALTI": 4,
        "ALTI": 8,
        "ORTALAMA": 12,
        "ÜSTÜ": 16,
        "ÇOK ÜSTÜ": 20,
    }

    for kolon, puan in kolon_puanlari.items():
        if kolon in norm_satiri and aralik_uyuyor_mu(deger, norm_satiri[kolon]):
            return puan

    return 4


def sheet_oku(norm_dosya, sheet_adi):
    excel = pd.ExcelFile(norm_dosya)
    sayfalar = {str(s).strip(): s for s in excel.sheet_names}

    if sheet_adi not in sayfalar:
        raise ValueError(f"Norm dosyasında '{sheet_adi}' sayfası bulunamadı. Mevcut sayfalar: {excel.sheet_names}")

    return pd.read_excel(norm_dosya, sheet_name=sayfalar[sheet_adi])


def yas_hesapla(ham):
    dogum_tarihi_col = kolon_bul(ham, ["DOĞUM TARİHİ", "DOGUM TARIHI"])
    dogum_yili_col = kolon_bul(ham, ["DOĞUM YILI", "DOGUM YILI"])

    if dogum_tarihi_col:
        ham["YAŞ"] = pd.Timestamp.now().year - pd.to_datetime(ham[dogum_tarihi_col], errors="coerce").dt.year
    elif dogum_yili_col:
        ham["YAŞ"] = pd.Timestamp.now().year - pd.to_numeric(ham[dogum_yili_col], errors="coerce")
    else:
        ham["YAŞ"] = 0

    ham["YAŞ"] = ham["YAŞ"].fillna(0).astype(int)
    return ham


def bacak_uzunlugu_hesapla(ham):
    bacak_col = kolon_bul(ham, ["BACAK BOYU", "BACAK BOY"])
    oturma_col = kolon_bul(ham, ["OTURMA YÜKSEKLİĞİ", "OTURMA YUKSEKLIGI", "OTURMA"])

    if bacak_col and oturma_col:
        uzunluklar = []
        puanlar = []

        for _, row in ham.iterrows():
            try:
                bacak = sayiya_cevir(row[bacak_col])
                oturma = sayiya_cevir(row[oturma_col])

                if bacak > oturma * 0.90:
                    uzunluklar.append("UZUN BACAK")
                    puanlar.append(20)
                else:
                    uzunluklar.append("KISA BACAK")
                    puanlar.append(4)

            except Exception:
                uzunluklar.append("VERİ YOK")
                puanlar.append(4)

        ham["BACAK UZUNLUĞU"] = uzunluklar
        ham["BACAK UZUNLUĞU PUAN"] = puanlar

    else:
        ham["BACAK UZUNLUĞU"] = "VERİ YOK"
        ham["BACAK UZUNLUĞU PUAN"] = 4

    return ham


def islem_yap(ham, norm_dosya):
    ham = yas_hesapla(ham)
    ham = bacak_uzunlugu_hesapla(ham)

    for test in TESTLER:
        puan_sutunu = f"{test} PUAN"

        if test == "FONKSİYONEL ÇÖMELME":
            if test in ham.columns:
                ham[puan_sutunu] = ham[test].apply(fonksiyonel_puanla)
            else:
                ham[puan_sutunu] = 4
            continue

        if test not in ham.columns:
            ham[puan_sutunu] = 4
            continue

        sayfa = TEST_SAYFA_ESLESME[test]
        norm = sheet_oku(norm_dosya, sayfa)

        puanlar = []

        for _, row in ham.iterrows():
            cinsiyet = temizle_metin(row["CİNSİYET"])
            yas = row["YAŞ"]

            norm_satirlari = norm[
                (norm["CİNSİYET"].astype(str).str.upper().str.strip() == cinsiyet)
                & (norm["YAŞ"] == yas)
            ]

            if norm_satirlari.empty:
                puanlar.append(4)
            else:
                puanlar.append(norm_puanla(row[test], norm_satirlari.iloc[0]))

        ham[puan_sutunu] = puanlar

    for brans, bilgi in BRANS_KRITERLERI.items():
        sonuclar = []
        sira_puanlari = []

        for _, row in ham.iterrows():
            yas = row["YAŞ"]
            cinsiyet = temizle_metin(row["CİNSİYET"])

            if yas not in bilgi["yas"] or cinsiyet not in bilgi["cinsiyet"]:
                sonuclar.append("REFERANS DIŞI")
                sira_puanlari.append(0)
                continue

            basarili = 0
            kalite = 0

            for test in bilgi["kriterler"]:
                puan = row[f"{test} PUAN"]

                if puan >= 12:
                    basarili += 1

                kalite += puan

            sonuclar.append(f"{basarili}/5 - {kalite}")
            sira_puanlari.append(basarili * 1000 + kalite)

        ham[f"{brans} SONUÇ"] = sonuclar
        ham[f"{brans} SIRA"] = sira_puanlari

    branslar = list(BRANS_KRITERLERI.keys())
    onerilenler = []

    for _, row in ham.iterrows():
        en_yuksek = max(row[f"{b} SIRA"] for b in branslar)

        if en_yuksek == 0:
            onerilenler.append("REFERANS DIŞI")
        else:
            secilenler = [b for b in branslar if row[f"{b} SIRA"] == en_yuksek]
            onerilenler.append(", ".join(secilenler))

    ham["ÖNERİLEN BRANŞ"] = onerilenler
    return ham


def excel_olustur(ham):
    temel_sutunlar = [
        "S.N.", "KURUM", "BÖLGE", "İLÇE", "ANTRENÖR ADI", "ÜYE NO",
        "AD SOYAD", "OKUL", "TC KİMLİK", "DOĞUM\nTARİHİ",
        "DOĞUM\nYILI", "CİNSİYET", "VELİ TELEFON 1",
    ]

    test_ve_puan_sutunlari = []

    for test in CIKTI_TEST_SIRASI:
        if test in ham.columns and test not in test_ve_puan_sutunlari:
            test_ve_puan_sutunlari.append(test)

        puan_sutunu = f"{test} PUAN"

        if puan_sutunu in ham.columns and puan_sutunu not in test_ve_puan_sutunlari:
            test_ve_puan_sutunlari.append(puan_sutunu)

    brans_sutunlari = [
        "KARATE SONUÇ",
        "TEKVANDO SONUÇ",
        "BOKS SONUÇ",
        "JUDO SONUÇ",
        "GÜREŞ SONUÇ",
        "ÖNERİLEN BRANŞ",
    ]

    kolonlar = [
        c for c in temel_sutunlar + test_ve_puan_sutunlari + brans_sutunlari
        if c in ham.columns
    ]

    temiz = ham[kolonlar].copy()

    output = BytesIO()
    temiz.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active
    basliklar = [cell.value for cell in ws[1]]

    for test in CIKTI_TEST_SIRASI:
        puan_sutunu = f"{test} PUAN"

        if test not in basliklar or puan_sutunu not in ham.columns:
            continue

        col_no = basliklar.index(test) + 1

        for i in range(len(temiz)):
            puan = ham.iloc[i][puan_sutunu]

            if puan in RENKLER:
                fill = PatternFill(
                    start_color=RENKLER[puan],
                    end_color=RENKLER[puan],
                    fill_type="solid",
                )

                ws.cell(row=i + 2, column=col_no).fill = fill

    ince_kenar = Side(style="thin", color="000000")

    tam_kenarlik = Border(
        left=ince_kenar,
        right=ince_kenar,
        top=ince_kenar,
        bottom=ince_kenar,
    )

    for row in ws.iter_rows():
        for cell in row:
            cell.font = Font(name="Calibri", size=12)
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )
            cell.border = tam_kenarlik

    for row_num in range(1, ws.max_row + 1):
        ws.row_dimensions[row_num].height = 30

    for column_cells in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column_cells[0].column)

        for cell in column_cells:
            if cell.value is not None:
                cell_value = str(cell.value)
                longest_line = max(len(line) for line in cell_value.split("\n"))
                max_length = max(max_length, longest_line)

        adjusted_width = max_length + 3
        adjusted_width = max(10, min(adjusted_width, 35))
        ws.column_dimensions[column_letter].width = adjusted_width

    final = BytesIO()
    wb.save(final)
    final.seek(0)

    return final


if ham_dosya and norm_dosya:
    ham = pd.read_excel(ham_dosya)

    st.success("Dosyalar başarıyla yüklendi.")

    metrik1, metrik2, metrik3 = st.columns(3)

    with metrik1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-number">{len(ham)}</div>
                <div class="metric-label">Yüklenen Öğrenci</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with metrik2:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-number">5</div>
                <div class="metric-label">Branş</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with metrik3:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-number">17</div>
                <div class="metric-label">Test / Ölçüm Alanı</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("Ham Veri Önizleme")
    st.dataframe(ham.head(), use_container_width=True)

    if st.button("Puanla ve Branşları Hesapla"):
        try:
            sonuc = islem_yap(ham.copy(), norm_dosya)

            st.write("İşlenen sonuç öğrenci sayısı:", len(sonuc))

            st.subheader("Filtreleme")

            filtre1, filtre2, filtre3, filtre4 = st.columns(4)

            with filtre1:
                secili_brans = st.selectbox(
                    "Branş Filtresi",
                    ["TÜMÜ"] + list(BRANS_KRITERLERI.keys()) + ["REFERANS DIŞI"]
                )

            with filtre2:
                if "İLÇE" in sonuc.columns:
                    ilceler = sorted(sonuc["İLÇE"].dropna().astype(str).unique())
                    secili_ilce = st.selectbox("İlçe", ["TÜMÜ"] + list(ilceler))
                else:
                    secili_ilce = "TÜMÜ"

            with filtre3:
                if "CİNSİYET" in sonuc.columns:
                    cinsiyetler = sorted(sonuc["CİNSİYET"].dropna().astype(str).unique())
                    secili_cinsiyet = st.selectbox("Cinsiyet", ["TÜMÜ"] + list(cinsiyetler))
                else:
                    secili_cinsiyet = "TÜMÜ"

            with filtre4:
                if "YAŞ" in sonuc.columns:
                    yaslar = sorted(sonuc["YAŞ"].dropna().unique())
                    secili_yas = st.selectbox("Yaş", ["TÜMÜ"] + list(yaslar))
                else:
                    secili_yas = "TÜMÜ"

            filtreli = sonuc.copy()

            if secili_brans != "TÜMÜ":
                if secili_brans == "REFERANS DIŞI":
                    filtreli = filtreli[filtreli["ÖNERİLEN BRANŞ"] == "REFERANS DIŞI"]
                else:
                    filtreli = filtreli[
                        filtreli["ÖNERİLEN BRANŞ"].astype(str).str.contains(secili_brans, na=False)
                    ]

            if secili_ilce != "TÜMÜ":
                filtreli = filtreli[filtreli["İLÇE"].astype(str) == str(secili_ilce)]

            if secili_cinsiyet != "TÜMÜ":
                filtreli = filtreli[filtreli["CİNSİYET"].astype(str) == str(secili_cinsiyet)]

            if secili_yas != "TÜMÜ":
                filtreli = filtreli[filtreli["YAŞ"] == secili_yas]

            st.subheader("Dashboard")

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric("Filtrelenen Sporcu", len(filtreli))

            with d2:
                referans_disi = len(filtreli[filtreli["ÖNERİLEN BRANŞ"] == "REFERANS DIŞI"])
                st.metric("Referans Dışı", referans_disi)

            with d3:
                st.metric("Branşa Uygun", len(filtreli) - referans_disi)

            if len(filtreli) > 0:
                st.subheader("Branş Dağılımı")

                brans_sayim = (
                    filtreli["ÖNERİLEN BRANŞ"]
                    .value_counts()
                    .reset_index()
                )

                brans_sayim.columns = ["Branş", "Sayı"]

                fig = px.bar(
                    brans_sayim,
                    x="Branş",
                    y="Sayı",
                    text="Sayı"
                )

                fig.update_layout(
                    height=500,
                    xaxis_title="Branş",
                    yaxis_title="Sporcu Sayısı"
                )

                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Sonuç Önizleme")

            gorunecek_kolonlar = [
                "AD SOYAD",
                "İLÇE",
                "YAŞ",
                "CİNSİYET",
                "KARATE SONUÇ",
                "TEKVANDO SONUÇ",
                "BOKS SONUÇ",
                "JUDO SONUÇ",
                "GÜREŞ SONUÇ",
                "ÖNERİLEN BRANŞ",
            ]

            gorunecek_kolonlar = [c for c in gorunecek_kolonlar if c in filtreli.columns]

            st.dataframe(
                filtreli[gorunecek_kolonlar],
                use_container_width=True,
                height=500
            )

            excel_dosya = excel_olustur(sonuc)

            st.download_button(
                label="Sonuç Excel Dosyasını İndir",
                data=excel_dosya,
                file_name="USGEP_SONUCLAR.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(str(e))
else:
    st.info("Lütfen ham test dosyasını ve norm tablo dosyasını yükleyin.")
