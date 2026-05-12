import streamlit as st
import pandas as pd
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
def yas_hesapla(yas_degeri):
    yas_degeri = int(yas_degeri)

    if yas_degeri > 1000:
        return 2026 - yas_degeri

    return yas_degeri


def sayiya_cevir(deger):
    if pd.isna(deger):
        return None

    return float(str(deger).replace(",", ".").strip())


def norm_puani_bul(norm_df, test_adi, cinsiyet, yas, sonuc):
    if sonuc in [None, "", 0, 0.0] or pd.isna(sonuc):
        return None

    yas = yas_hesapla(yas)
    cinsiyet = str(cinsiyet).strip().upper()

    satirlar = norm_df[
        (norm_df["CİNSİYET"].astype(str).str.upper() == cinsiyet)
        & (norm_df["YAŞ"].astype(int) == yas)
    ]

    if satirlar.empty:
        return None

    satir = satirlar.iloc[0]

    kategoriler = {
        "ÇOK ALTI": 1,
        "ALTI": 2,
        "ORTALAMA": 3,
        "ÜSTÜ": 4,
        "ÇOK ÜSTÜ": 5
    }

    sonuc = float(sonuc)

    for kategori, puan in kategoriler.items():
        aralik = str(satir[kategori]).replace(",", ".").strip()
        aralik = aralik.replace(",", ".")

        if "≤" in aralik:
            limit = sayiya_cevir(aralik.replace("≤", ""))
            if sonuc <= limit:
                return puan

        elif "≥" in aralik:
            limit = sayiya_cevir(aralik.replace("≥", ""))
            if sonuc >= limit:
                return puan

        elif "-" in aralik:

            aralik = aralik.replace(" ", "")
            parcalar = aralik.split("-")

            if len(parcalar) != 2:
                continue

            a = sayiya_cevir(parcalar[0])
            b = sayiya_cevir(parcalar[1])

            if a is None or b is None:
                continue

            alt = min(a, b)
            ust = max(a, b)

            if alt <= sonuc <= ust:
                return puan

    return None

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

    sporcular = sporculari_getir()
    testler = testleri_getir()

    norm_dosya = Path(__file__).parent / "NORM TABLO ÖN TESTLER.xlsx"

    if not norm_dosya.exists():

        st.error("Norm dosyası bulunamadı. GitHub'a 'NORM TABLO ÖN TESTLER.xlsx' dosyasını yükleyin.")

    elif sporcular.empty or testler.empty:

        st.warning("Sporcu veya test verisi bulunamadı.")

    else:

        sonuc = testler.merge(
            sporcular,
            left_on="sporcu_id",
            right_on="id",
            how="left",
            suffixes=("_test", "_sporcu")
        )

        st.subheader("Ön Test Sporcu Listesi")
        st.dataframe(sonuc, use_container_width=True)

        st.divider()

        st.subheader("Puanlama Sistemi")

        if st.button("Ön Test Puanlarını Hesapla"):

            normlar = pd.read_excel(
                norm_dosya,
                sheet_name=None
            )

            puanli = sonuc.copy()

            test_eslestirme = {
                "BOY": "boy",
                "KULAÇ": "kulac",
                "DURARAK UZUN ATLAMA": "durarak_uzun_atlama",
                "20 M. SPRINT": "sprint20",
                "OTUR UZAN": "otur_uzan",
                "MEKİK": "mekik"
            }

            for norm_sayfa, test_kolonu in test_eslestirme.items():

                puan_kolonu = f"{test_kolonu}_puan"

                if test_kolonu not in puanli.columns:
                    puanli[puan_kolonu] = None
                    continue

                norm_df = normlar[norm_sayfa]

                puanlar = []

                for _, row in puanli.iterrows():

                    deger = row[test_kolonu]

                    if test_kolonu == "boy" and deger not in [None, "", 0, 0.0] and float(deger) < 3:
                        deger = float(deger) * 100

                    puan = norm_puani_bul(
                        norm_df=norm_df,
                        test_adi=norm_sayfa,
                        cinsiyet=row["cinsiyet"],
                        yas=row["yas"],
                        sonuc=deger
                    )

                    puanlar.append(puan)

                puanli[puan_kolonu] = puanlar

            puan_kolonlari = [
                kolon for kolon in puanli.columns
                if kolon.endswith("_puan")
            ]

            puanli["toplam_puan"] = puanli[puan_kolonlari].sum(axis=1, skipna=True)

            st.success("Ön test puanları hesaplandı.")

            st.subheader("Puanlı Ön Test Sonuçları")
            st.dataframe(puanli, use_container_width=True)

            
            from io import BytesIO

            buffer = BytesIO()

            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                puanli.to_excel(writer, index=False, sheet_name="Ön Test Puanları")

            st.download_button(
                label="📥 Ön Test Excel Çıktısını İndir",
                data=buffer.getvalue(),
                file_name="on_test_puanli_sonuclar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


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

    st.info("Bu sayfada branş yönlendirme puanlama, renklendirme ve Excel çıktısı yapılacak.")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    st.subheader("Sporcu Verileri")
    st.dataframe(sporcular, use_container_width=True)

    st.subheader("Test Verileri")
    st.dataframe(testler, use_container_width=True)


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

