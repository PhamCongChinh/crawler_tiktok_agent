class PageManager:
    def __init__(self, context):
        self.context = context

    async def new_page(self):
        return await self.context.new_page()

    async def new_blank_page(self):
        page = await self.context.new_page()
        await page.goto("about:blank")
        return page
