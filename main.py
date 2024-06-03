from quart import Quart, request, jsonify
from bs4 import BeautifulSoup
import cfscrape
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Quart(__name__)
base_url = "https://komikcast.lol"

scraper = cfscrape.create_scraper()
executor = ThreadPoolExecutor(max_workers=10)

async def fetch(url):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(executor, scraper.get, url)
    return response.text, response.status_code

@app.route("/terbaru", methods=["GET"])
async def terbaru():
    page = request.args.get("page")
    if not page:
        return jsonify({"status": "failed", "message": "page is required"}), 500
    
    html, status_code = await fetch(f"{base_url}/project-list/page/{page}")
    if status_code == 200:
        komik_list = []
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper > .postbody > .bixbox")
        current_page = element.select_one(".pagination > .page-numbers.current").text.strip()
        
        length_page = None
        for nth in [5, 7, 8, 9, 10]:
            page_element = element.select_one(f".pagination > .page-numbers:nth-child({nth})")
            if page_element and "next page-numbers" in page_element.get("class", []):
                length_page = element.select_one(f".pagination > .page-numbers:nth-child({nth-1})").text.strip()
                break
            if page_element and "page-numbers current" in page_element.get("class", []):
                length_page = element.select_one(f".pagination > .page-numbers:nth-child({nth})").text.strip()
                break

        for data in element.select(".list-update_items > .list-update_items-wrapper > .list-update_item"):
            thumbnail = data.select_one("a > .list-update_item-image > img").get("src")
            href = data.select_one("a").get("href")
            type = data.select_one("a > .list-update_item-image > .type").text.strip()
            title = data.select_one("a > .list-update_item-info > h3").text.strip()
            chapter = data.select_one("a > .list-update_item-info > .other > .chapter").text.strip()
            rating = data.select_one("a > .list-update_item-info > .other > .rate > .rating > .numscore").text.strip()
            komik_list.append({
                "title": title,
                "href": href.replace(f"{base_url}/komik", "").strip(),
                "thumbnail": thumbnail,
                "type": type,
                "chapter": chapter,
                "rating": rating
            })

        return jsonify({
            "status": "success",
            "current_page": float(current_page),
            "length_page": float(length_page) if length_page else None,
            "data": komik_list
        }), 200
    
    return jsonify({"status": "failed", "message": "failed"}), status_code

@app.route("/genre/<url>", methods=["GET"])
async def genre(url):
    page = request.args.get("page")
    if not page:
        return jsonify({"status": "failed", "message": "page is required"}), 500
    
    html, status_code = await fetch(f"{base_url}/genres/{url}/page/{page}")
    if status_code == 200:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper > .postbody > .bixbox")
        komik_list = []

        check_pagination = element.select_one(".listupd > .list-update_items > .pagination > .current").text.strip()
        length_page = None

        for nth in [5, 7, 8, 9, 10]:
            page_element = element.select_one(f".pagination > .page-numbers:nth-child({nth})")
            if page_element and "next page-numbers" in page_element.get("class", []):
                length_page = element.select_one(f".pagination > .page-numbers:nth-child({nth-1})").text.strip()
                break
            if page_element and "page-numbers current" in page_element.get("class", []):
                length_page = element.select_one(f".pagination > .page-numbers:nth-child({nth})").text.strip()
                break

        for data in element.select(".listupd > .list-update_items > .list-update_items-wrapper > .list-update_item"):
            title = data.select_one("a > .list-update_item-info > h3").text.strip()
            chapter = data.select_one("a > .list-update_item-info > .other > .chapter").text.strip()
            type = data.select_one("a > .list-update_item-image > .type").text.strip()
            thumbnail = data.select_one("a > .list-update_item-image > img").get("src")
            rating = data.select_one("a > .list-update_item-info > .other > .rate > .rating > .numscore").text.strip()
            href = data.select_one("a").get("href")
            komik_list.append({
                "title": title,
                "chapter": chapter,
                "type": type,
                "href": href.replace(f"{base_url}/komik", "").strip(),
                "rating": rating,
                "thumbnail": thumbnail
            })

        return jsonify({
            "status": "success",
            "current_page": int(check_pagination) if check_pagination else 1,
            "length_page": float(length_page) if length_page else None,
            "data": komik_list
        }), 200
    
    return jsonify({"status": "failed", "message": "failed"}), status_code

@app.route("/genre", methods=["GET"])
async def genre_list():
    html, status_code = await fetch(base_url)
    if status_code == 200:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper")
        komik_list = []
        for data in element.select("#sidebar > .section > ul.genre > li"):
            title = data.select_one("a").text.strip()
            href = data.select_one("a").get("href")
            komik_list.append({
                "title": title,
                "href": href.replace(f"{base_url}/genres", "").strip()
            })
        return jsonify({"status": "success", "data": komik_list}), 200
    return jsonify({"status": "failed", "message": "failed"}), status_code

@app.route("/read/<url>", methods=["GET"])
async def read(url):
    try:
        html, status_code = await fetch(f"{base_url}/{url}")
        if status_code == 200:
            soup = BeautifulSoup(html, 'html.parser')
            element = soup.select_one("#content > .wrapper")
            if element:
                komik_detail = {}

                prev_chapter_element = element.select_one(
                    ".chapter_nav-control > .right-control > .nextprev > a[rel='prev']"
                )
                next_chapter_element = element.select_one(
                    ".chapter_nav-control > .right-control > .nextprev > a[rel='next']"
                )

                prev_chapter = prev_chapter_element.get("href").replace(f"{base_url}/chapter", "") if prev_chapter_element else None
                next_chapter = next_chapter_element.get("href").replace(f"{base_url}/chapter", "") if next_chapter_element else None

                title_element = element.select_one(".chapter_headpost > h1")
                title = title_element.text.strip() if title_element else "N/A"

                panel = []
                for data in element.select(".chapter_ > #chapter_body > .main-reading-area img"):
                    panel_src = data.get("src")
                    if panel_src:
                        panel.append(panel_src)

                komik_detail["title"] = title
                komik_detail["prev"] = prev_chapter
                komik_detail["next"] = next_chapter
                komik_detail["panel"] = panel

                return jsonify({"status": "success", "data": komik_detail}), 200

            return jsonify({"status": "failed", "message": "comic details not found"}), 404

        if status_code == 404:
            return jsonify({"status": "failed", "message": "comic not found"}), 404

        return jsonify({"status": "failed", "message": "failed"}), status_code
    except Exception as e:
        print(e)
        return jsonify({"status": "failed", "message": "An error occurred"}), 500

@app.route("/search", methods=["GET"])
async def search():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"status": "failed", "message": "keyword is required"}), 500
    
    html, status_code = await fetch(f"{base_url}/?s={keyword}&post_type=wp-manga")
    if status_code == 200:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper")
        komik_list = []
        for data in element.select(".list-update_items > .list-update_items-wrapper > .list-update_item"):
            title = data.select_one("a > .list-update_item-info > h3").text.strip()
            href = data.select_one("a").get("href")
            type = data.select_one("a > .list-update_item-image > .type").text.strip()
            rating = data.select_one("a > .list-update_item-info > .other > .rate > .rating > .numscore").text.strip()
            chapter = data.select_one("a > .list-update_item-info > .other > .chapter").text.strip()
            thumbnail = data.select_one("a > .list-update_item-image > img").get("src")
            komik_list.append({
                "title": title,
                "type": type,
                "chapter": chapter,
                "rating": rating,
                "href": href.replace(f"{base_url}/komik", "").strip(),
                "thumbnail": thumbnail
            })
        
        return jsonify({"status": "success", "data": komik_list}), 200
    
    return jsonify({"status": "failed", "message": "failed"}), status_code

@app.route("/detail/<url>", methods=["GET"])
async def detail(url):
    try:
        html, status_code = await fetch(f"{base_url}/manga/{url}")
        if status_code == 200:
            soup = BeautifulSoup(html, 'html.parser')
            element = soup.select_one("#content > .wrapper > .komik_info")
            if element:
                komik_detail = {}

                rating_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-rating > .komik_info-content-rating-bungkus > .data-rating > strong"
                )
                komik_detail["rating"] = rating_element.text.strip().replace("Rating ", "") if rating_element else "N/A"

                title_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > h1"
                )
               
                
                komik_detail["title"] = title_element.text.strip() if title_element else "N/A"

                alt_title_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-native"
                )
                komik_detail["altTitle"] = alt_title_element.text.strip() if alt_title_element else "N/A"

                released_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-meta > span:nth-child(1)"
                )
                komik_detail["released"] = released_element.text.strip().replace("Released:", "").strip() if released_element else "N/A"

                updateOn_element = element.select_one(".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-meta > .komik_info-content-update")
                komik_detail["updateOn"] = updateOn_element.text.strip().replace("UpdateOn:","").strip() if updateOn_element else "N/A"

                author_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-meta > span:nth-child(2)"
                )
                komik_detail["author"] = author_element.text.strip().replace("Author:", "").strip() if author_element else "N/A"

                status_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-meta > span:nth-child(3)"
                )
                komik_detail["status"] = status_element.text.strip().replace("Status:", "").strip() if status_element else "N/A"

                type_element = element.select_one(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-meta > span:nth-child(4)"
                )
                komik_detail["type"] = type_element.text.strip().replace("Type:", "").strip() if type_element else "N/A"

                description_element = element.select_one(".komik_info-description-sinopsis > p")
                komik_detail["description"] = description_element.text.strip() if description_element else "N/A"

                thumbnail_element = element.select_one(".komik_info-cover-box > .komik_info-cover-image > img")
                komik_detail["thumbnail"] = thumbnail_element.get("src") if thumbnail_element else "N/A"

                komik_detail["chapters"] = []
                for data in element.select(".komik_info-body > .komik_info-chapters > ul > li"):
                    title_element = data.select_one("a")
                    href_element = data.select_one("a").get("href")
                    date_element = data.select_one(".chapter-link-time")

                    title = title_element.text.strip() if title_element else "N/A"
                    href = href_element.replace(f"{base_url}/chapter", "").strip() if href_element else "N/A"
                    date = date_element.text.strip() if date_element else "N/A"

                    komik_detail["chapters"].append({
                        "title": f"Chapter {title.replace('Chapter', '').strip()}",
                        "href": href,
                        "date": date
                    })

                komik_detail["genre"] = []
                for data in element.select(
                    ".komik_info-body > .komik_info-content > .komik_info-content-body > .komik_info-content-genre > a"
                ):
                    genre_title_element = data
                    genre_href_element = data.get("href")

                    genre_title = genre_title_element.text.strip() if genre_title_element else "N/A"
                    genre_href = genre_href_element.replace(f"{base_url}/genres", "").strip() if genre_href_element else "N/A"

                    komik_detail["genre"].append({
                        "title": genre_title,
                        "href": genre_href
                    })

                return jsonify({"status": "success", "data": komik_detail}), 200

            return jsonify({"status": "failed", "message": "comic details not found"}), 404

        if status_code == 404:
            return jsonify({"status": "failed", "message": "comic not found"}), 404

        return jsonify({"status": "failed", "message": "failed"}), status_code
    except Exception as e:
        print(e)
        return jsonify({"status": "failed", "message": "An error occurred"}), 500

@app.route("/popular", methods=["GET"])
async def popular():
    html, status_code = await fetch(base_url)
    if status_code == 200:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper > #sidebar")
        komik_list = []

        for data in element.select(".section > .widget-post > .serieslist.pop > ul > li"):
            title = data.select_one(".leftseries > h2 > a").text.strip()
            year = data.select_one(".leftseries > span:nth-child(3)").text.strip()
            genre = data.select_one(".leftseries > span:nth-child(2)").text.strip().replace("Genres:", "").strip()
            thumbnail = data.select_one(".imgseries > a > img").get("src")
            href = data.select_one(".imgseries > a").get("href")
            komik_list.append({
                "title": title,
                "href": href.replace(f"{base_url}/komik", "").strip(),
                "genre": genre,
                "year": year,
                "thumbnail": thumbnail
            })

        return jsonify({"status": "success", "data": komik_list}), 200
    
    return jsonify({"status": "failed", "message": "failed"}), status_code

@app.route("/recommended", methods=["GET"])
async def recommended():
    html, status_code = await fetch(base_url)
    if status_code == 200:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.select_one("#content > .wrapper > .bixbox > .listupd > .swiper > .swiper-wrapper")
        komik_list = []

        for data in element.select(".swiper-slide"):
            title = data.select_one("a > .splide__slide-info > .title").text.strip()
            rating = data.select_one("a > .splide__slide-info > .other > .rate > .rating > .numscore").text.strip()
            chapter = data.select_one("a > .splide__slide-info > .other > .chapter").text.strip()
            type = data.select_one("a > .splide__slide-image > .type").text.strip()
            href = data.select_one("a").get("href")
            thumbnail = data.select_one("a > .splide__slide-image > img").get("src")
            komik_list.append({
                "title": title,
                "href": href.replace(f"{base_url}/komik", "").strip(),
                "rating": rating,
                "chapter": chapter,
                "type": type,
                "thumbnail": thumbnail
            })

        komik_list = [komik for komik in komik_list if komik.get("href")]

        return jsonify({"status": "success", "data": komik_list}), 200
    
    return jsonify({"status": "failed", "message": "failed"}), status_code

if __name__ == "__main__":
    app.run(port=8000,debug=True)

