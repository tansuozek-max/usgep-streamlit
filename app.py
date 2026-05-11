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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def sporculari_getir():
    data = supabase.table("sporcular").select("*").order("id").execute()
    return pd.DataFrame(data.data)


def testleri_getir():
    data = supabase.table("testler").select("*").order("id").execute()
    return pd.DataFrame(data.data)


with st.sidebar:
    logo_yolu = Path(__file__).parent / "logo.png"

    if logo_yolu.exists():
        st.image(str(logo_yolu), width=180)

    st.title("USGEP Menü")

    sayfa = st.radio(
        "Sayfa Seç",
        [
            "🏠 Ana Sayfa",
            "🧒 Sporcu Kayıt",
            "📋 Test Veri Girişi",
            "📊 Sonuçlar",
            "📈 Dashboard"
        ]
    )

test_modu = st.query_params.get("test", "normal")

if sayfa == "🏠 Ana Sayfa":

    st.title("USGEP Branş Yönlendirme Sistemi")

    st.markdown("""
    ### Sistem Durumu

    ✅ Online erişim aktif  
    ✅ Tablet erişimi aktif  
    ✅ Streamlit Cloud yayında  
    ✅ Supabase veritabanı bağlı  

    ---
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tablet", "6")

    with col2:
        st.metric("Branş", "5")

    with col3:
        st.metric("Test Alanı", "17")


elif sayfa == "🧒 Sporcu Kayıt":

    st.title("Sporcu Kayıt")

    with st.form("sporcu_form"):
        ad = st.text_input("Ad Soyad")
        yas = st.number_input("Yaş", 5, 18)
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

                st.success("Sporcu Supabase veritabanına kaydedildi.")


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
            supabase.table("testler").insert({
                "sporcu_id": sporcu_id,
                "boy": float(boy),
                "kilo": float(kilo),
                "sprint20": float(sprint20),
                "dikey_sicrama": float(dikey_sicrama)
            }).execute()

            st.success("Test verileri Supabase veritabanına kaydedildi.")


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

    if not sporcular.empty:

        sporcular["secim"] = (
            sporcular["id"].astype(str)
            + " - "
            + sporcular["ad_soyad"]
        )

        secili = st.selectbox(
            "Sporcu",
            sporcular["secim"]
        )

        sporcu_id = int(
            secili.split(" - ")[0]
        )

        mevcut = supabase.table(
            "testler"
        ).select("*").eq(
            "sporcu_id",
            sporcu_id
        ).execute()

        mevcut_veri = None

        if mevcut.data:
            mevcut_veri = mevcut.data[0].get(test["kolon"])

        admin_sifre = st.sidebar.text_input(
            "Admin Şifresi",
            type="password"
        )

        admin_mi = admin_sifre == "1234"

        kilitli = (
            mevcut_veri not in [None, 0, 0.0, ""]
            and not admin_mi
        )

        if kilitli:

            st.warning(
                "Bu test sonucu daha önce kaydedilmiş."
            )

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
                value=float(mevcut_veri)
                if mevcut_veri not in [None, ""]
                else 0.0
            )

            if st.button("Kaydet"):

                if mevcut.data:

                    supabase.table(
                        "testler"
                    ).update({
                        test["kolon"]: float(sonuc)
                    }).eq(
                        "sporcu_id",
                        sporcu_id
                    ).execute()

                else:

                    veri = {
                        "sporcu_id": sporcu_id,
                        test["kolon"]: float(sonuc)
                    }

                    supabase.table(
                        "testler"
                    ).insert(
                        veri
                    ).execute()

                st.success(
                    f'{test["etiket"]} kaydedildi.'
                )

                st.rerun()
