import asyncio
from bs4 import BeautifulSoup
import pandas as pd
from playwright.async_api import async_playwright


class İlanlarGovTrScraper:

    def __init__(self, headless: bool = True):
        self.base_url = "https://www.ilan.gov.tr"
        # İhale kategorisi / arama sayfası URL'si
        self.target_url = f"{self.base_url}/ilan/kategori/9/ihale-ilanlari"
        self.headless = headless

    async def run(self, max_pages: int = 3):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            print(f"[+] Sayfaya bağlanılıyor: {self.target_url}")
            await page.goto(self.target_url, wait_until="networkidle", timeout=60000)

            all_ihaler = []

            for current_page in range(1, max_pages + 1):
                print(f"[+] Sayfa {current_page} işleniyor...")

                # İçeriğin tam yüklenmesi için bekleme
                await page.wait_for_timeout(3000)

                # Sayfa kaynağını alıp BeautifulSoup ile ayrıştırıyoruz
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                cards = soup.select("div.ng-star-inserted")
                print(f"[i] Sayfada bulunan ilan bloğu sayısı: {len(cards)}")

                # Sayfadaki linkleri ve ihale başlıklarını çekiyoruz
                links = await page.locator("a").all()
                for link in links:
                    href = await link.get_attribute("href")
                    title = await link.inner_text()
                    if href and "/ilan/" in href and len(title.strip()) > 10:
                        full_link = (
                            href
                            if href.startswith("http")
                            else f"{self.base_url}{href}"
                        )
                        all_ihaler.append({"Baslik": title.strip(), "Link": full_link})

                # Sonraki sayfaya geçiş işlemi
                next_btn = page.locator("a[title='Sonraki']")

                if current_page < max_pages:
                    if await next_btn.is_visible():
                        print("[+] 'Sonraki' butonuna tıklanıyor...")
                        await next_btn.click()
                        # Tıkladıktan sonra yeni verilerin API'den gelmesini beklemek için kısa bir duraklama
                        await page.wait_for_timeout(2000)
                    else:
                        print(
                            "[-] 'Sonraki' butonu bulunamadı veya son sayfaya gelindi."
                        )
                        break

            await browser.close()

            # Tekilleştirme ve Temizlik
            df = pd.DataFrame(all_ihaler).drop_duplicates(subset=["Link"])
            print(f"\n[✓] Toplam {len(df)} adet benzersiz ihale bulundu.")
            return df


if __name__ == "__main__":

    async def main():
        scraper = İlanlarGovTrScraper(headless=False)
        # max_pages parametresini 5 yaparak ilk 5 sayfayı kazıyabilirsin
        df = await scraper.run(max_pages=5)

        print(df.head())

        # CSV Olarak Kaydetme
        df.to_csv("ihaleler_raw.csv", index=False, encoding="utf-8-sig")
        print("[✓] Veriler ihaleler_raw.csv olarak kaydedildi.")

        # JSON Olarak Kaydetme
        df.to_json("ihaleler_raw.json", orient="records", force_ascii=False, indent=4)
        print("[✓] Veriler ihaleler_raw.json olarak kaydedildi.")

    asyncio.run(main())
