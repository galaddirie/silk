import asyncio
from typing import List
from pydantic import BaseModel

from silk.actions.navigation import Navigate
from silk.actions.elements  import QueryAll, GetText
from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.models   import BrowserOptions, ElementHandle, ActionContext
from silk.browsers.sessions import BrowserSession
from silk.objects import build
from silk.composition import Map
from silk import Operation


class BookDetails(BaseModel):
    title: str
    price: str

extract_book_details = build({
    "title": GetText("h3 > a"),
    "price": GetText("p.price_color"),
}, BookDetails)

pipeline: Operation[[ElementHandle], List[BookDetails]] = (
    Navigate("https://books.toscrape.com/")  # load the page
    >> QueryAll("article.product_pod")       # returns List[ElementHandle]
    >> Map(extract_book_details)  # type: ignore  
)

async def main() -> None:
    opts = BrowserOptions(
        headless=False,
        browser_type="chromium",
        viewport_width=1280,
        viewport_height=800,
    )

    async with BrowserSession(options=opts, driver_class=PlaywrightDriver) as ctx:
        print("Starting scraper for books.toscrape.com…")
        result = await pipeline(context=ctx).execute()

        books = result.default_value([])
        if not books:
            print("No books found.")
            return

        print(f"Found {len(books)} books:")

        for idx, book in enumerate(books, 1):
            if isinstance(book, BookDetails):
                print(f"  {idx:2}. {book.title} — {book.price}")
            else:
                print(f"  {idx:2}. {book}")

if __name__ == "__main__":
    asyncio.run(main())
