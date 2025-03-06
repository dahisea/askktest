import asyncio
import httpx
import uvloop
import numpy as np

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())












# 预定义的 User-Agent 和 IP 列表
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

# 预生成随机 User-Agent 和 IP 列表
def generate_random_headers_and_ips(num_requests):
    user_agent_list = np.random.choice(user_agents, num_requests)
    ip_list = np.random.choice(random_ips, num_requests)
    return list(zip(user_agent_list, ip_list))

async def download_dependency(client, method, url, stats, no_response, headers):
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
        print(f"Request failed: {e}")

async def worker(client, queue, stats, method, no_response):
    while not queue.empty():
        url, headers = await queue.get()
        await download_dependency(client, method, url, stats, no_response, headers)
        queue.task_done()

async def main():
    total_downloads = 100000
    num_concurrent_requests = 5000  # 增加并发量
    download_method = "GET"
    no_response_needed = False

    download_stats = {
        'total_requests': 0,
        'total_responses': 0,
        'non_200_responses': 0,
        'total_response_size': 0
    }

    # 预生成随机 headers 和 IPs
    headers_and_ips = generate_random_headers_and_ips(total_downloads)

    # 配置连接池和复用连接以提高性能
    limits = httpx.Limits(max_keepalive_connections=100000, max_connections=100000)
    timeout = httpx.Timeout(timeout=30.0)  # 设置超时时间
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        queue = asyncio.Queue()

        # 填充队列
        for headers in headers_and_ips:
            await queue.put((dependency_url, {"User-Agent": headers[0], "X-Real-IP": headers[1]}))

        # 创建并启动 worker 任务
        tasks = []
        for _ in range(num_concurrent_requests):
            task = asyncio.create_task(worker(client, queue, download_stats, download_method, no_response_needed))
            tasks.append(task)

        # 等待队列中的所有任务完成
        await queue.join()

        # 取消所有 worker 任务
        for task in tasks:
            task.cancel()

        # 等待所有 worker 任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

    print(f"总下载次数: {download_stats['total_requests']}")
    print(f"成功下载次数: {download_stats['total_responses']}")
    print(f"下载失败次数: {download_stats['non_200_responses']}")
    print(f"总响应流量: {download_stats['total_response_size']} bytes")
    print("依赖下载完成")

if __name__ == "__main__":
    asyncio.run(main())
