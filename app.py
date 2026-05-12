import streamlit as st
import pandas as pd
import re
from datetime import date
from io import BytesIO
from pathlib import Path
from supabase import create_client

st.set_page_config(
    page_title="USGEP Branş Yönlendirme",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def sporculari_getir():
    data = supabase.table("sporcular").select("*").order("id").execute()
    return pd.DataFrame(data.data)


def testleri_getir():
    data = supabase.table("testler").select("*").order("id").execute()
    return pd.DataFrame(data.data)


def temiz_deger_mi(deger):
    return deger not in [None, "", 0, 0.0]


BRANS_TESTLERI = [
    ("BOY", "boy", "BOY"),
    ("KİLO", "kilo", "KİLO"),
    ("KULAÇ", "kulac", "KULAÇ"),
    ("EL ÇABUKLUĞU", "el_cabuklugu", "EL ÇABUKLUĞU"),
    ("AYAK ÇABUKLUĞU", "ayak_cabuklugu", "AYAK ÇABUKLUĞU"),
    ("EL KAVRAMA", "el_kavrama", "EL KAVRAMA"),
    ("SIRT BACAK", "sirt_bacak", "SIRT BACAK KUVVETİ"),
    ("HEXAGON", "hexagon", "HEXAGON"),
    ("DURARAK UZUN ATLAMA", "durarak_uzun_atlama", "DURARAK UZUN ATLAMA"),
    ("GERİYE SAĞLIK TOPU ATMA", "geriye_saglik_topu", "GERİYE SAĞLIK TOPU FIRLATMA"),
    ("DİKEY SIÇRAMA", "dikey_sicrama", "DİKEY SIÇRAMA"),
    ("LANE AGILITY", "lane_ceviklik", "LANE ÇEVİKLİK"),
    ("20 M. SPRINT", "sprint20", "20 M. SPRINT"),
]

NORM_PUANLARI = {
    "ÇOK ALTI": 4,
    "ALTI": 8,
    "ORTALAMA": 12,
    "ÜSTÜ": 16,
    "ÇOK ÜSTÜ": 20,
}


def _metin_norm(metin):
    return str(metin).strip().upper().replace("İ", "I")


def _sayi_yap(deger):
    if pd.isna(deger):
        return None
    if isinstance(deger, (int, float)):
        return float(deger)
    temiz = str(deger).strip().replace(",", ".")
    try:
        return float(temiz)
    except ValueError:
        return None


def _yas_hesapla(deger):
    yas = _sayi_yap(deger)
    if yas is None:
        return None
    yas = int(yas)
    if yas > 1900:
        return date.today().year - yas
    return yas


def _norm_dosyasi_bul():
    adaylar = [
        Path(__file__).parent / "NORM TABLO.xlsx",
        Path(__file__).parent / "NORM TABLO(5).xlsx",
        Path.home() / "Desktop" / "NORM TABLO.xlsx",
        Path.home() / "Desktop" / "NORM TABLO(5).xlsx",
    ]
    for yol in adaylar:
        if yol.exists():
            return yol
    return None


def _normlari_oku(kaynak):
    sayfalar = pd.read_excel(kaynak, sheet_name=None, engine="openpyxl")
    return {str(ad).strip().upper(): df for ad, df in sayfalar.items()}


def _aralik_uyuyor_mu(ifade, deger):
    if pd.isna(ifade) or deger is None:
        return False

    metin = str(ifade).strip().replace(",", ".")
    sayilar = [float(s) for s in re.findall(r"\d+(?:\.\d+)?", metin)]

    if not sayilar:
        return False

    if "≤" in metin or "<=" in metin:
        return deger <= sayilar[0]

    if "≥" in metin or ">=" in metin:
        return deger >= sayilar[0]

    if len(sayilar) >= 2:
        alt = min(sayilar[0], sayilar[1])
        ust = max(sayilar[0], sayilar[1])
        return alt <= deger <= ust

    return deger == sayilar[0]


def _norm_puani(normlar, sayfa_adi, cinsiyet, yas, deger):
    deger = _sayi_yap(deger)
    yas = _yas_hesapla(yas)

    if deger is None or yas is None or not cinsiyet:
        return None

    df = normlar.get(sayfa_adi.strip().upper())
    if df is None:
        return None

    df = df.copy()
    df.columns = [str(k).strip().upper() for k in df.columns]

    if "CİNSİYET" not in df.columns or "YAŞ" not in df.columns:
        return None

    satirlar = df[
        (df["CİNSİYET"].map(_metin_norm) == _metin_norm(cinsiyet))
        & (pd.to_numeric(df["YAŞ"], errors="coerce") == yas)
    ]

    if satirlar.empty:
        return None

    satir = satirlar.iloc[0]
    for kolon, puan in NORM_PUANLARI.items():
        if kolon in satir and _aralik_uyuyor_mu(satir[kolon], deger):
            return puan

    return None


def _ilk_dolu_satir_degeri(satir, kolonlar):
    for kolon in kolonlar:
        if kolon in satir and pd.notna(satir[kolon]):
            return satir[kolon]
    return None


def brans_amacli_sonuclari_hazirla(sporcular, testler, normlar):
    birlesik = testler.merge(
        sporcular,
        left_on="sporcu_id",
        right_on="id",
        how="left",
        suffixes=("_test", "_sporcu"),
    )

    satirlar = []

    for sira, (_, satir) in enumerate(birlesik.iterrows(), start=1):
        yas_degeri = _ilk_dolu_satir_degeri(
            satir,
            ["yas", "yas_sporcu", "doğum_yılı", "dogum_yili", "dogum_yılı", "dogum_yili_sporcu"],
        )
        cinsiyet = _ilk_dolu_satir_degeri(satir, ["cinsiyet", "cinsiyet_sporcu", "cinsiyet_test"])

        sonuc = {
            "S.N.": sira,
            "İLÇE": _ilk_dolu_satir_degeri(satir, ["ilce", "ilçe"]),
            "AD SOYAD": _ilk_dolu_satir_degeri(satir, ["ad_soyad", "ad soyad"]),
            "DOĞUM YILI": yas_degeri,
            "YAŞ": _yas_hesapla(yas_degeri),
            "CİNSİYET": cinsiyet,
        }

        puan_kolonlari = []

        for baslik, veri_kolonu, norm_sayfasi in BRANS_TESTLERI:
            deger = satir[veri_kolonu] if veri_kolonu in satir else None
            puan = _norm_puani(normlar, norm_sayfasi, cinsiyet, yas_degeri, deger)
            puan_kolon = f"{baslik} PUAN"

            sonuc[baslik] = deger
            sonuc[puan_kolon] = puan
            puan_kolonlari.append(puan_kolon)

        sonuc["TOPLAM PUAN"] = sum(sonuc[k] for k in puan_kolonlari if sonuc[k] is not None)
        satirlar.append(sonuc)

    return pd.DataFrame(satirlar)


def _puan_renk_css(deger):
    renkler = {
        4: "background-color: #f4cccc;",
        8: "background-color: #fce5cd;",
        12: "background-color: #fff2cc;",
        16: "background-color: #d9ead3;",
        20: "background-color: #b6d7a8;",
    }
    return renkler.get(deger, "")


def brans_excel_olustur(df):
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    cikti = BytesIO()

    with pd.ExcelWriter(cikti, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Branş Amaçlı")
        ws = writer.sheets["Branş Amaçlı"]

        header_fill = PatternFill("solid", fgColor="D9EAF7")
        total_fill = PatternFill("solid", fgColor="B4C6E7")
        fills = {
            4: PatternFill("solid", fgColor="F4CCCC"),
            8: PatternFill("solid", fgColor="FCE5CD"),
            12: PatternFill("solid", fgColor="FFF2CC"),
            16: PatternFill("solid", fgColor="D9EAD3"),
            20: PatternFill("solid", fgColor="B6D7A8"),
        }
        ince = Side(style="thin", color="D9D9D9")
        kenarlik = Border(left=ince, right=ince, top=ince, bottom=ince)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = kenarlik

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                baslik = ws.cell(1, cell.column).value
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = kenarlik

                if baslik and "PUAN" in str(baslik):
                    cell.fill = fills.get(cell.value, PatternFill(fill_type=None))

                if baslik == "TOPLAM PUAN":
                    cell.fill = total_fill
                    cell.font = Font(bold=True)

        for col in ws.columns:
            baslik = str(col[0].value or "")
            genislik = min(max(len(baslik) + 2, 10), 28)
            ws.column_dimensions[col[0].column_letter].width = genislik

    cikti.seek(0)
    return cikti.getvalue()


SAYFALAR = [
    "🏠 Ana Sayfa",
    "🧒 Sporcu Kayıt",
    "📋 Test Veri Girişi",
    "📊 Sonuçlar",
    "📈 Dashboard",
    "🧪 Ön Testler",
    "🇪🇺 Eurofit",
    "🏅 Branş Amaçlı",
]

with st.sidebar:
    logo_yolu = Path(__file__).parent / "logo.png"

    if logo_yolu.exists():
        st.image(str(logo_yolu), width=180)

    st.title("USGEP Menü")
    sayfa = st.radio("Sayfa seç", SAYFALAR, label_visibility="collapsed")

test_modu = st.query_params.get("test", "normal")


# ---------------------------
# ANA SAYFA
# ---------------------------

if sayfa == "🏠 Ana Sayfa":

    st.title("USGEP Branş Yönlendirme Sistemi")

    st.markdown("""
    ### Sistem Durumu

    ✅ Online erişim aktif  
    ✅ Tablet erişimi aktif  
    ✅ Streamlit Cloud yayında  
    ✅ Supabase veritabanı bağlı  
    ✅ QR istasyon sistemi aktif  
    ✅ Admin yetkili düzenleme aktif  

    ---
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tablet", "6")

    with col2:
        st.metric("Branş", "5")

    with col3:
        st.metric("Test Alanı", "17")


# ---------------------------
# SPORCU KAYIT
# ---------------------------

elif sayfa == "🧒 Sporcu Kayıt":

    st.title("Sporcu Kayıt")

    st.subheader("Tekli Sporcu Kayıt")

    with st.form("tekli_sporcu_kayit_formu"):

        ad = st.text_input("Ad Soyad")
        yas = st.number_input("Doğum Yılı", 2000, 2025)
        cinsiyet = st.selectbox("Cinsiyet", ["ERKEK", "KIZ"])
        ilce = st.text_input("İlçe")

        submit = st.form_submit_button("Kaydet")

        if submit:
            if not ad.strip():
                st.warning("Ad soyad boş bırakılamaz.")
            else:
                supabase.table("sporcular").insert({
                    "ad_soyad": ad.strip(),
                    "yas": int(yas),
                    "cinsiyet": cinsiyet,
                    "ilce": ilce.strip()
                }).execute()

                st.success("Sporcu kaydedildi.")

    st.divider()

    st.subheader("Excel ile Toplu Sporcu Yükleme")

    st.info("Excel sütunları şu şekilde olmalı: ad_soyad | yas | cinsiyet | ilce")

    dosya = st.file_uploader(
        "Excel Dosyası Yükle",
        type=["xlsx"]
    )

    if dosya is not None:

        try:
            df = pd.read_excel(dosya)

            df.columns = (
                df.columns
                .astype(str)
                .str.strip()
                .str.lower()
            )

            st.write("Önizleme")
            st.dataframe(df.head(), use_container_width=True)

            gerekli_kolonlar = [
                "ad_soyad",
                "yas",
                "cinsiyet",
                "ilce"
            ]

            eksik = [
                kolon for kolon in gerekli_kolonlar
                if kolon not in df.columns
            ]

            if eksik:
                st.error(f"Eksik sütunlar: {eksik}")

            else:
                if st.button("Toplu Yüklemeyi Başlat"):

                    df = df[gerekli_kolonlar].copy()

                    df["ad_soyad"] = df["ad_soyad"].astype(str).str.strip()
                    df["yas"] = df["yas"].astype(int)
                    df["cinsiyet"] = df["cinsiyet"].astype(str).str.strip().str.upper()
                    df["ilce"] = df["ilce"].astype(str).str.strip()

                    df = df[df["ad_soyad"] != ""]

                    veriler = df.to_dict(orient="records")

                    if len(veriler) == 0:
                        st.warning("Yüklenecek geçerli sporcu bulunamadı.")
                    else:
                        supabase.table("sporcular").insert(veriler).execute()
                        st.success(f"{len(veriler)} sporcu başarıyla yüklendi.")

        except Exception as e:
            st.error(f"Hata oluştu: {e}")


# ---------------------------
# NORMAL TEST VERİ GİRİŞİ
# ---------------------------

elif sayfa == "📋 Test Veri Girişi":

    st.title("Test Veri Girişi")

    sporcular = sporculari_getir()

    if sporcular.empty:
        st.warning("Önce sporcu kaydı oluşturun.")
    else:
        sporcular["secim"] = sporcular["id"].astype(str) + " - " + sporcular["ad_soyad"]

        secili = st.selectbox("Sporcu Seç", sporcular["secim"])
        sporcu_id = int(secili.split(" - ")[0])

        st.subheader("Testler")

        boy = st.number_input("Boy", min_value=0.0, step=0.1)
        kilo = st.number_input("Kilo", min_value=0.0, step=0.1)
        sprint20 = st.number_input("20m Sprint", min_value=0.0, step=0.01)
        dikey_sicrama = st.number_input("Dikey Sıçrama", min_value=0.0, step=0.1)

        if st.button("Testleri Kaydet"):
            mevcut = supabase.table("testler").select("*").eq("sporcu_id", sporcu_id).execute()

            veri = {
                "sporcu_id": sporcu_id,
                "boy": float(boy),
                "kilo": float(kilo),
                "sprint20": float(sprint20),
                "dikey_sicrama": float(dikey_sicrama)
            }

            if mevcut.data:
                supabase.table("testler").update(veri).eq("sporcu_id", sporcu_id).execute()
            else:
                supabase.table("testler").insert(veri).execute()

            st.success("Test verileri kaydedildi.")


# ---------------------------
# SONUÇLAR
# ---------------------------

elif sayfa == "📊 Sonuçlar":

    st.title("Sonuçlar")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    if testler.empty:
        st.info("Henüz test sonucu bulunmuyor.")
    else:
        if not sporcular.empty:
            sonuc = testler.merge(
                sporcular,
                left_on="sporcu_id",
                right_on="id",
                how="left",
                suffixes=("_test", "_sporcu")
            )
        else:
            sonuc = testler

        st.dataframe(sonuc, use_container_width=True)


# ---------------------------
# DASHBOARD
# ---------------------------

elif sayfa == "📈 Dashboard":

    st.title("Dashboard")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Toplam Sporcu", len(sporcular))

    with col2:
        st.metric("Toplam Test Kaydı", len(testler))

    st.subheader("Sporcu Listesi")
    st.dataframe(sporcular, use_container_width=True)

    st.subheader("Test Listesi")
    st.dataframe(testler, use_container_width=True)

# ---------------------------
# ÖN TESTLER
# ---------------------------

elif sayfa == "🧪 Ön Testler":

    st.title("Ön Testler")

    st.info("Bu sayfada ön test sonuçları, puanlama ve Excel çıktı işlemleri yapılacak.")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    st.subheader("Sporcu Verileri")
    st.dataframe(sporcular, use_container_width=True)

    st.subheader("Test Verileri")
    st.dataframe(testler, use_container_width=True)


# ---------------------------
# EUROFIT
# ---------------------------

elif sayfa == "🇪🇺 Eurofit":

    st.title("Eurofit")

    st.info("Bu sayfada Eurofit testleri için değerlendirme, puanlama ve renklendirme yapılacak.")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    st.subheader("Sporcu Verileri")
    st.dataframe(sporcular, use_container_width=True)

    st.subheader("Test Verileri")
    st.dataframe(testler, use_container_width=True)


# ---------------------------
# BRANŞ AMAÇLI
# ---------------------------

elif sayfa == "🏅 Branş Amaçlı":

    st.title("Branş Amaçlı")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    if sporcular.empty:
        st.warning("Önce sporcu kaydı oluşturun.")
    elif testler.empty:
        st.warning("Henüz test sonucu bulunmuyor.")
    else:
        norm_dosyasi = _norm_dosyasi_bul()
        yuklenen_norm = st.file_uploader(
            "Norm tablosu",
            type=["xlsx"],
            help="NORM TABLO.xlsx bulunamazsa buradan yükleyebilirsiniz.",
        )

        kaynak = yuklenen_norm if yuklenen_norm is not None else norm_dosyasi

        if kaynak is None:
            st.error("NORM TABLO.xlsx bulunamadı. Norm dosyasını bu sayfadan yükleyin.")
        else:
            try:
                normlar = _normlari_oku(kaynak)
                sonuc = brans_amacli_sonuclari_hazirla(sporcular, testler, normlar)

                puan_kolonlari = [kolon for kolon in sonuc.columns if "PUAN" in kolon]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Sporcu", len(sonuc))
                with col2:
                    st.metric("Puanlanan Test", len(puan_kolonlari) - 1)
                with col3:
                    st.metric("En Yüksek Toplam", int(sonuc["TOPLAM PUAN"].max()))

                st.subheader("Branş Amaçlı Puanlama Sonuçları")

                st.dataframe(
                    sonuc.style.applymap(_puan_renk_css, subset=puan_kolonlari),
                    use_container_width=True,
                    hide_index=True,
                )

                excel = brans_excel_olustur(sonuc)

                st.download_button(
                    "Excel Çıktısını İndir",
                    data=excel,
                    file_name="brans_amacli_puanlama.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            except Exception as e:
                st.error(f"Branş amaçlı puanlama oluşturulamadı: {e}")


# ---------------------------
# QR / TEST İSTASYON MODU
# ---------------------------

TEST_ISTASYONLARI = {

    "boy": {
        "baslik": "Boy Ölçüm İstasyonu",
        "kolon": "boy",
        "etiket": "Boy",
        "birim": "cm",
        "step": 0.1
    },

    "kilo": {
        "baslik": "Kilo Ölçüm İstasyonu",
        "kolon": "kilo",
        "etiket": "Kilo",
        "birim": "kg",
        "step": 0.1
    },

    "kulac": {
        "baslik": "Kulaç Ölçüm İstasyonu",
        "kolon": "kulac",
        "etiket": "Kulaç",
        "birim": "cm",
        "step": 0.1
    },

    "durarak_uzun_atlama": {
        "baslik": "Durarak Uzun Atlama İstasyonu",
        "kolon": "durarak_uzun_atlama",
        "etiket": "Durarak Uzun Atlama",
        "birim": "cm",
        "step": 0.1
    },

    "dikey_sicrama": {
        "baslik": "Dikey Sıçrama İstasyonu",
        "kolon": "dikey_sicrama",
        "etiket": "Dikey Sıçrama",
        "birim": "cm",
        "step": 0.1
    },

    "el_kavrama": {
        "baslik": "El Kavrama İstasyonu",
        "kolon": "el_kavrama",
        "etiket": "El Kavrama",
        "birim": "kg",
        "step": 0.1
    },

    "geriye_saglik_topu": {
        "baslik": "Geriye Sağlık Topu İstasyonu",
        "kolon": "geriye_saglik_topu",
        "etiket": "Geriye Sağlık Topu",
        "birim": "m",
        "step": 0.1
    },

    "sprint": {
        "baslik": "20m Sprint İstasyonu",
        "kolon": "sprint20",
        "etiket": "20m Sprint",
        "birim": "sn",
        "step": 0.01
    },

    "ayak_cabuklugu": {
        "baslik": "Ayak Çabukluğu İstasyonu",
        "kolon": "ayak_cabuklugu",
        "etiket": "Ayak Çabukluğu",
        "birim": "sn",
        "step": 0.01
    },

    "el_cabuklugu": {
        "baslik": "El Çabukluğu İstasyonu",
        "kolon": "el_cabuklugu",
        "etiket": "El Çabukluğu",
        "birim": "adet",
        "step": 1.0
    },

    "sirt_bacak": {
        "baslik": "Sırt Bacak Kuvveti İstasyonu",
        "kolon": "sirt_bacak",
        "etiket": "Sırt Bacak Kuvveti",
        "birim": "kg",
        "step": 0.1
    },

    "hexagon": {
        "baslik": "Hexagon İstasyonu",
        "kolon": "hexagon",
        "etiket": "Hexagon",
        "birim": "sn",
        "step": 0.01
    },

    "lane_ceviklik": {
        "baslik": "Lane Çeviklik İstasyonu",
        "kolon": "lane_ceviklik",
        "etiket": "Lane Çeviklik",
        "birim": "sn",
        "step": 0.01
    }
}


if test_modu in TEST_ISTASYONLARI:

    test = TEST_ISTASYONLARI[test_modu]

    st.title(test["baslik"])

    sporcular = sporculari_getir()

    if sporcular.empty:
        st.warning("Henüz sporcu kaydı yok.")
    else:

        sporcular["secim"] = (
            sporcular["id"].astype(str)
            + " - "
            + sporcular["ad_soyad"]
        )

        secili = st.selectbox(
            "Sporcu",
            sporcular["secim"]
        )

        sporcu_id = int(secili.split(" - ")[0])

        mevcut = supabase.table("testler").select("*").eq("sporcu_id", sporcu_id).execute()

        mevcut_veri = None

        if mevcut.data:
            mevcut_veri = mevcut.data[0].get(test["kolon"])

        admin_sifre = st.sidebar.text_input(
            "Admin Şifresi",
            type="password"
        )

        admin_mi = admin_sifre == ADMIN_PASSWORD

        kilitli = temiz_deger_mi(mevcut_veri) and not admin_mi

        if kilitli:

            st.warning("Bu test sonucu daha önce kaydedilmiş. Düzenleme yetkiniz yok.")

            st.number_input(
                f'{test["etiket"]} ({test["birim"]})',
                value=float(mevcut_veri),
                disabled=True
            )

        else:

            sonuc = st.number_input(
                f'{test["etiket"]} ({test["birim"]})',
                min_value=0.0,
                step=test["step"],
                value=float(mevcut_veri) if temiz_deger_mi(mevcut_veri) else 0.0
            )

            if st.button("Kaydet"):

                if mevcut.data:

                    supabase.table("testler").update({
                        test["kolon"]: float(sonuc)
                    }).eq(
                        "sporcu_id",
                        sporcu_id
                    ).execute()

                else:

                    supabase.table("testler").insert({
                        "sporcu_id": sporcu_id,
                        test["kolon"]: float(sonuc)
                    }).execute()

                st.success(f'{test["etiket"]} kaydedildi.')
                st.rerun()

