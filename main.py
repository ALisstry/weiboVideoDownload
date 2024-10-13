import requests
import os
import argparse
from tqdm import tqdm
import json
import time

def extract_urls_from_data(data):
    """从嵌套数据结构中提取所有 playback_list 的 URL"""
    urls = []

    def recursive_search(obj):
        if isinstance(obj, dict):
            playback_list = obj.get('playback_list', [])
            if playback_list and 'play_info' in playback_list[0]:
                url = playback_list[0]['play_info'].get('url')
                if url:
                    urls.append(url)
        
            for value in obj.values():
                recursive_search(value)
        elif isinstance(obj, list):
            for item in obj:
                recursive_search(item)

    recursive_search(data)
    return urls

def get_video_urls(user_id):
    base_url = "https://weibo.com/ajax/profile/getWaterFallContent"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": f"https://weibo.com/u/{user_id}",
        "Sec-Ch-Ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Cookie": "XSRF-TOKEN=0qQ_MqO_I4RHBuFG3bpruHBZ; SUB=_2AkMQV-SDf8NxqwFRmf0dymjgbIh1zgjEieKmCxVYJRMxHRl-yj9vqmk-tRB6O9fKbJZBu4XwmHISCaGF6LSFL2OYESu9; SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9WhHu3GZ9fm0qFX5hSmg1Wk8; WBPSESS=Av_uyMf5J_yRg2sn7ncLQUvgnXiXoQnEB_XGd-QQ8ApWINzofrIy_C-LzrJXszyo_K5wMDdRQRJec_AqXes1DUWsPkCW4cez3K607E0G_t-5NGyzcFMZb8ifqG3GA78r"
    }
    
    all_urls = []  # 用于存储所有提取的 URL
    next_cursor = 0  # 将 next_cursor 初始化为 0

    while True:
        if next_cursor == -1:
            print("No more pages to fetch. Exiting.")
            break  # 在请求之前检查 next_cursor 的值

        response = requests.get(f"{base_url}?uid={user_id}&cursor={next_cursor}", headers=headers)

        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content: {response.text[:200]}")  # Print first 200 chars for debugging
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if "data" in data and "list" in data["data"]:
                    if data["data"]["list"]:  # If there's any content in list
                        current_urls = extract_urls_from_data(data)  # 提取 URL
                        all_urls.extend(current_urls)  # 将当前提取的 URL 添加到总列表
                        print(f"URLs found in this request: {len(current_urls)}")  # 打印当前请求找到的 URL数量

                        next_cursor = data["data"].get("next_cursor", -1)  # 如果 next_cursor 为 -1 则停止
                        print(f"Next Cursor: {next_cursor}")  # Print next_cursor value
                    else:
                        print("No more videos found.")
                        break

                else:
                    print("Unexpected data structure.")
                    break

            except json.JSONDecodeError:
                print("JSON decoding failed. The response content may not be valid JSON.")
                break
        else:
            # 处理 400 错误
            print(f"Failed to get data, status code: {response.status_code}")
            if response.status_code == 400:
                print("Bad request encountered. Exiting.")
                break
            
        # 防止请求过于频繁，等待一段时间再请求
        time.sleep(2)  # 等待 2 秒

    return all_urls

def download_video(url, output_path):
    """下载视频并保存到指定路径"""
    if not os.path.exists(output_path):
        os.makedirs(output_path)  # 创建目标文件夹

    # 获取视频文件名
    file_name = url.split("/")[-1].split("?")[0]  # 获取文件名，不包含查询参数
    file_path = os.path.join(output_path, file_name)

    # 检查文件是否已经存在
    if os.path.exists(file_path):
        print(f"文件已存在，跳过下载: {file_name}")
        return True  # 返回True表示文件已存在

    # 下载视频
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_length = int(response.headers.get('content-length', 0))
        with open(file_path, 'wb') as file:
            if total_length == 0:
                file.write(response.content)  # 如果无法获取文件大小，直接写入
            else:
                with tqdm(total=total_length, unit='B', unit_scale=True, desc=file_name) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                        pbar.update(len(chunk))
        print(f"下载完成: {file_name}")
        return True  # 返回True表示下载成功
    else:
        print(f"下载失败: {url}")
        return False  # 返回False表示下载失败

def save_urls_to_file(video_urls, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        for url in video_urls:
            file.write(url + "\n")
    print(f"All URLs have been saved to {filename}")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Weibo Video Downloader')
    parser.add_argument('-user_id', type=str, required=True, help='Weibo user ID')
    parser.add_argument('-output_path', type=str, default='downloads', help='Output path for downloaded videos')
    args = parser.parse_args()
    
    # 配置参数
    user_id = args.user_id  # 从命令行获取 Weibo 用户 ID
    output_path = os.path.join(args.output_path, user_id)  # 使用 user_id 创建子文件夹

    # 获取所有视频 URL
    video_urls = get_video_urls(user_id)

    # 打印总结信息
    print(f"Total URLs found: {len(video_urls)}")
    if video_urls:
        save_urls_to_file(video_urls, "video_urls.txt")  # 保存 URL 列表

        # 下载视频并处理中断
        total_count = len(video_urls)
        success_count = 0
        fail_count = 0

        for index, url in enumerate(video_urls, start=1):  # 使用 enumerate 来跟踪已下载的文件数量
            print(f"\n下载文件 {index}/{total_count}...")
            try:
                if download_video(url, output_path):
                    success_count += 1
                else:
                    fail_count += 1
            except KeyboardInterrupt:
                print("\n下载中断，正在删除未完成的文件...")
                if os.path.exists(os.path.join(output_path, url.split("/")[-1])):
                    os.remove(os.path.join(output_path, url.split("/")[-1]))
                print("未完成的文件已删除。")
                break

        # 打印总结信息
        print(f"\n下载总结：")
        print(f"总共文件数: {total_count}")
        print(f"成功下载: {success_count}")
        print(f"下载失败: {fail_count}")
    else:
        print("没有找到视频 URL。")
