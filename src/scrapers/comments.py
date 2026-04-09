import asyncio
import logging

from src.config.logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# async def crawl_tiktok_comment(context):
# 	page = await context.new_page()
# 	await postgresDB.connect()
# 	posts = await postgresDB.fetch_posts(1)
# 	for i, row in enumerate(posts, 1):
# 		unix_time = int(time.time() * 1000)
# 		url = row.get("url")
# 		org_id = row.get("org_id")

# 		url = f"https://www.tiktok.com/@angiang_new/video/7623022972009205000"

# 		print(url)
# 		print(org_id)

# 		await page.goto(url, wait_until="domcontentloaded")
# 		await page.wait_for_timeout(5000)
# 		# await page.wait_for_timeout(random.randint(60, 90))

# 		comments_by_video = []
# 		pending_tasks = []  # ✅ Track các task đang chạy
# 		async def on_response(res):
# 			try:
# 				if any(api in res.url for api in API_COMMENT):
# 					try:
# 						body = await res.json()
# 					except:
# 						return
# 					if not body:
# 						return

# 					comments = body.get("comments", [])

# 					request_url = res.url
# 					if not isinstance(request_url, str):
# 						return

# 					for c in comments:
# 						share_info = c.get("share_info") or {}
# 						user_info = c.get("user") or {}
# 						avatar = user_info.get("avatar_thumb", {}).get("url_list", [])

# 						comment_id = c.get("cid")
# 						pub_time = c.get("create_time")
# 						title = share_info.get("title")
# 						description = share_info.get("desc")
# 						content = c.get("text")
# 						#url = share_info.get("url")
# 						media = avatar[0] if avatar else None
# 						reactions = c.get("digg_count")
# 						auth_id = user_info.get("uid")
# 						auth_name = user_info.get("nickname")
# 						unique_id = user_info.get("unique_id")
# 						aweme_id = c.get("aweme_id")

# 						comments_data = {
# 							"org_id": org_id,
# 							"pub_time": pub_time,
# 							"comment_id": comment_id,
# 							"title": title,
# 							"description": description,
# 							"subject_id": comment_id,
# 							"content": content,
# 							"url": url,
# 							"media": media,
# 							"reaction": reactions,
# 							"auth_id": auth_id,
# 							"auth_name": auth_name,
# 							"unique_id": unique_id,
# 							"video_id": aweme_id
# 						}

# 						data = TiktokComment.new(comments_data)
# 						comments_by_video.append(data)

# 					print(f"💬 TOTAL COMMENTS FETCHED: {len(comments)}")
# 					print("=" * 50)
# 			except Exception as e:
# 				print("❌ ERROR:", e)

# 		def handle_response(res):
# 			task = asyncio.create_task(on_response(res))
# 			pending_tasks.append(task)  # ✅ Lưu lại task

# 		page.on("response", handle_response)
# 		await asyncio.sleep(random.randint(10, 30))
# 		await close_popup_if_any(page)
# 		await asyncio.sleep(random.randint(5, 10))
# 		await page.click('[data-e2e="comment-icon"]')
# 		await asyncio.sleep(random.randint(5, 10))

# 		# ✅ Chờ tất cả response handler xử lý xong TRƯỚC khi ghi file
# 		if pending_tasks:
# 			await asyncio.gather(*pending_tasks, return_exceptions=True)

#         # ✅ Ghi file SAU KHI đã thu thập đủ data
# 		# with open("results.json", "w", encoding="utf-8") as f:
# 		# 	json.dump(comments_by_video, f, indent=4, ensure_ascii=False)

# 		if comments_by_video:
# 			try:
# 				result = await postToESClassified(comments_by_video)
# 				logger.info(f"[] Posted {len(comments_by_video)} posts to API MASTER: {result.get('status')}")
# 			except Exception as e:
# 				logger.error(f"[] Error posting to API MASTER: {e}")

# 		page.remove_listener("response", handle_response)  # ✅ Dọn dẹp listener

# 	await postgresDB.close()
# 	rest_time = random.randint(600, 900)
# 	logger.info(f"😴 Resting {rest_time}s before next session")


# async def close_popup_if_any(page):
#     try:
#         await page.locator('div[class*="DivXMarkWrapper"]').click(timeout=2000)
#     except:
#         pass