#!/usr/bin/env python3
"""
API-Football 赛前赔率获取脚本（Pre-Match Odds）
按 fixture_id 获取赔率数据，并将完整响应保存为 JSON 文件。
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class APIFootballClient:
    """API-Football客户端类"""

    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError("请在 .env 文件或环境变量中设置 API_FOOTBALL_KEY")

        # API-Football 基础配置
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "v3.football.api-sports.io",
        }

    def get_odds_by_fixture(self, fixture_id: int) -> dict | None:
        """根据 fixture_id 获取赛前赔率数据。

        Args:
            fixture_id: 比赛 ID

        Returns:
            dict | None: API 完整响应（成功时），否则 None
        """
        url = f"{self.base_url}/odds"
        params = {"fixture": int(fixture_id)}

        print(f"请求URL: {url}")
        print(f"请求参数: {params}")

        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            print(f"HTTP状态码: {resp.status_code}")
            resp.raise_for_status()

            data = resp.json()
            # 简要统计
            resp_items = data.get("response", [])
            print(f"响应条目数: {len(resp_items)}")
            return data

        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            try:
                print(f"错误响应: {resp.text}")
            except Exception:
                pass
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            try:
                print(f"原始文本: {resp.text[:500]}")
            except Exception:
                pass
            return None

    @staticmethod
    def save_json(data: dict, output_dir: str, filename: str | None = None) -> str | None:
        """将数据保存为 JSON 文件。

        Args:
            data: 要保存的字典数据
            output_dir: 输出目录
            filename: 文件名；未提供则自动生成

        Returns:
            文件路径或 None
        """
        if not data:
            print("没有数据可保存")
            return None

        os.makedirs(output_dir, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"odds_{timestamp}.json"

        path = os.path.join(output_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到: {path}")
            return path
        except Exception as e:
            print(f"保存文件失败: {e}")
            return None


def main():
    """主函数：获取指定 fixture 的赔率并保存。"""
    fixture_id = 1412626  # 用户指定的 fixture
    print(f"🔍 开始获取 fixture_id={fixture_id} 的赛前赔率...")

    try:
        client = APIFootballClient()
        odds_data = client.get_odds_by_fixture(fixture_id)

        if odds_data is None:
            print("❌ 获取赔率数据失败或无数据")
            return

        output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
        filename = f"odds_fixture_{fixture_id}.json"
        saved = client.save_json(odds_data, output_dir, filename)

        if saved:
            print("✅ 赔率数据保存完成")
        else:
            print("❌ 赔率数据保存失败")

    except Exception as e:
        print(f"❌ 程序执行出错: {e}")


if __name__ == "__main__":
    main()