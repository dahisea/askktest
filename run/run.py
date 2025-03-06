import asyncio
import random
import httpx
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())





user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

random_ips = [
    "192.168.1.1",
    "192.168.0.1",
    "10.0.0.1",
    "127.0.0.1",
    "172.16.0.1",
    "0.0.0.0",
]


async def download_dependency(client, method, url, stats, no_response):
    headers = {
        "User-Agent": random.choice(user_agents),
        "X-Real-IP": random.choice(random_ips)
    }
    try:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers)
        elif method == "HEAD":
            response = await client.head(url, headers=headers)
        else:
            print(f"Unsupported method: {method}")
            return

        stats['total_requests'] += 1
        if not no_response:
            stats['total_response_size'] += len(response.content)
            if response.status_code != 200:
                stats['non_200_responses'] += 1
            else:
                stats['total_responses'] += 1
    except httpx.RequestError as e:
        print(f"Update failed: {e}")

async def main():
    total_downloads = 100000
    num_concurrent_requests = 1000
    download_method = "GET"
    no_response_needed = False

    download_stats = {
        'total_requests': 0,
        'total_responses': 0,
        'non_200_responses': 0,
        'total_response_size': 0
    }

    # 配置连接池和复用连接以提高性能
    limits = httpx.Limits(max_keepalive_connections=80000, max_connections=100000)
    async with httpx.AsyncClient(limits=limits, timeout=360) as client:
        semaphore = asyncio.Semaphore(num_concurrent_requests)
        tasks = []

        async def sem_task():
            async with semaphore:
                await download_dependency(client, download_method, dependency_url, download_stats, no_response_needed)

        for _ in range(total_downloads):
            tasks.append(sem_task())

        await asyncio.gather(*tasks)

    print(f"总下载次数: {download_stats['total_requests']}")
    print(f"成功下载次数: {download_stats['total_responses']}")
    print(f"下载失败次数: {download_stats['non_200_responses']}")
    print(f"总响应流量: {download_stats['total_response_size']} bytes")
    print("依赖下载完成")

if __name__ == "__main__":
    asyncio.run(main())
