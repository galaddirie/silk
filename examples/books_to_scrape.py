import asyncio

from silk.actions.elements import GetText, QueryAll
from silk.actions.navigation import Navigate
from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.models import BrowserOptions
from silk.browsers.sessions import BrowserSession
from silk.placeholder import _
from silk.composition import map

async def main():
    """
    Scrapes book titles and prices from books.toscrape.com.
    """
    options = BrowserOptions(
        headless=False,
        browser_type="chromium",
        viewport={"width": 1280, "height": 800}
    )


    extract_book_details = {
        "title": GetText("h3 > a"),
        "price": GetText("p.price_color")
    }

    # extract_book_details = {
    #     "title" << GetText("h3 > a"),
    #     "price" << GetText("p.price_color")
    }

    pipeline = (
        Navigate("https://books.toscrape.com/")
        >> QueryAll("article.product_pod")
        >> map(
    )

    async with BrowserSession(options=options, driver_class=PlaywrightDriver) as context:
        print("Starting scraper for books.toscrape.com...")
        result = await pipeline(context=context)

        if result.is_ok():
            books_data = result.default_value(None)
            
            if not books_data: # Check if the block is empty
                print("No books found on the page.")
                return

            print(f"Found {len(books_data)} books:")
            for i, book in enumerate(books_data):
                if book: # book itself is a Result a dict, check if it's not an error if map can fail per item
                    title = book.get("title", "N/A")
                    price = book.get("price", "N/A")
                    print(f"  {i+1}. Title: {title}, Price: {price}")
                else:
                    print(f"  {i+1}. Error extracting book details.")
            
            # If books_data can be None from result.ok_value in some scenarios
            if books_data is None:
                 print("No data returned from scraping pipeline.")

        else:
            print(f"An error occurred: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
