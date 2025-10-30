import http.client
import os
import json
import datetime
import logging
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import argparse

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataSaver:
    def __init__(self, db_url: str = None, timezone: str = "UTC"):
        """
        初始化DataSaver类
        
        参数:
            db_url: 数据库连接URL，如果为None则从环境变量读取
            timezone: 时区字符串（默认 UTC），用于API查询
        """
        self.db_url = db_url
        self.connection = None
        self.timezone = timezone
        
        # 从环境变量获取数据库连接信息（bc_agent/.env）
        if not self.db_url:
            self.db_config = {
                'host': os.getenv('postgre_host'),
                'port': int(os.getenv('postgre_port', 5432)),
                'database': os.getenv('postgre_db'),
                'user': os.getenv('postgre_user'),
                'password': os.getenv('postgre_password')
            }
        
        # API配置
        self.api_key = os.getenv('API_FOOTBALL_KEY')
        if not self.api_key:
            raise ValueError("未找到 API_FOOTBALL_KEY 环境变量")
        
        logger.info("DataSaver初始化完成")
    
    def connect_db(self) -> bool:
        """
        连接到PostgreSQL数据库
        
        返回:
            bool: 连接是否成功
        """
        try:
            if self.db_url:
                self.connection = psycopg2.connect(self.db_url)
            else:
                self.connection = psycopg2.connect(**self.db_config)
            
            self.connection.autocommit = True
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def disconnect_db(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("数据库连接已断开")
    
    def create_fixtures_table(self) -> bool:
        """
        创建fixtures表
        
        返回:
            bool: 表创建是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS fixtures (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER UNIQUE NOT NULL,
            fixture_referee VARCHAR(255),
            fixture_timezone VARCHAR(100),
            fixture_date TIMESTAMP,
            fixture_timestamp BIGINT,
            fixture_venue_id INTEGER,
            fixture_venue_name VARCHAR(255),
            fixture_venue_city VARCHAR(255),
            fixture_status_long VARCHAR(100),
            fixture_status_short VARCHAR(20),
            fixture_status_elapsed INTEGER,
            league_id INTEGER,
            league_name VARCHAR(255),
            league_country VARCHAR(255),
            league_logo VARCHAR(500),
            league_flag VARCHAR(500),
            league_season INTEGER,
            league_round VARCHAR(255),
            teams_home_id INTEGER,
            teams_home_name VARCHAR(255),
            teams_home_logo VARCHAR(500),
            teams_home_winner BOOLEAN,
            teams_away_id INTEGER,
            teams_away_name VARCHAR(255),
            teams_away_logo VARCHAR(500),
            teams_away_winner BOOLEAN,
            goals_home INTEGER,
            goals_away INTEGER,
            score_halftime_home INTEGER,
            score_halftime_away INTEGER,
            score_fulltime_home INTEGER,
            score_fulltime_away INTEGER,
            score_extratime_home INTEGER,
            score_extratime_away INTEGER,
            score_penalty_home INTEGER,
            score_penalty_away INTEGER,
            raw_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_fixtures_fixture_id ON fixtures(fixture_id);
        CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures(fixture_date);
        CREATE INDEX IF NOT EXISTS idx_fixtures_league_id ON fixtures(league_id);
        CREATE INDEX IF NOT EXISTS idx_fixtures_teams ON fixtures(teams_home_id, teams_away_id);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_sql)
            logger.info("fixtures表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建fixtures表失败: {e}")
            return False
    
    def get_fixtures_by_date(self, date_str: str = None) -> Optional[List[Dict[Any, Any]]]:
        """
        通过日期获取比赛信息
        
        参数:
            date_str: 日期字符串，格式为YYYY-MM-DD，默认为当天
        
        返回:
            List[Dict]: 比赛数据列表，如果失败返回None
        """
        # 如果没有提供日期，使用当天日期
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            conn = http.client.HTTPSConnection("v3.football.api-sports.io")
            
            headers = {
                'x-rapidapi-host': "v3.football.api-sports.io",
                'x-rapidapi-key': self.api_key
            }
            
            # 构建请求URL
            endpoint = f"/fixtures?date={date_str}&timezone={self.timezone}"
            
            logger.info(f"正在获取{date_str}的比赛信息（时区: {self.timezone}）...")
            logger.info(f"请求URL: {endpoint}")
            
            conn.request("GET", endpoint, headers=headers)
            
            res = conn.getresponse()
            data = res.read()
            
            # 解析JSON数据
            data_json = json.loads(data.decode("utf-8"))
            
            # 检查API响应
            if "response" in data_json:
                fixtures_data = data_json["response"]
                logger.info(f"成功获取 {len(fixtures_data)} 场比赛信息")
                return fixtures_data
            else:
                logger.error("API返回数据中没有找到response字段")
                return None
                
        except Exception as e:
            logger.error(f"获取比赛数据失败: {e}")
            return None
    
    def save_fixtures_to_db(self, fixtures_data: List[Dict[Any, Any]]) -> bool:
        """
        将比赛数据保存到数据库
        
        参数:
            fixtures_data: 比赛数据列表
        
        返回:
            bool: 保存是否成功
        """
        if not self.connection:
            if not self.connect_db():
                return False
        
        if not fixtures_data:
            logger.warning("没有数据需要保存")
            return True
        
        insert_sql = """
        INSERT INTO fixtures (
            fixture_id, fixture_referee, fixture_timezone, fixture_date, fixture_timestamp,
            fixture_venue_id, fixture_venue_name, fixture_venue_city,
            fixture_status_long, fixture_status_short, fixture_status_elapsed,
            league_id, league_name, league_country, league_logo, league_flag, league_season, league_round,
            teams_home_id, teams_home_name, teams_home_logo, teams_home_winner,
            teams_away_id, teams_away_name, teams_away_logo, teams_away_winner,
            goals_home, goals_away,
            score_halftime_home, score_halftime_away,
            score_fulltime_home, score_fulltime_away,
            score_extratime_home, score_extratime_away,
            score_penalty_home, score_penalty_away,
            raw_data
        ) VALUES (
            %(fixture_id)s, %(fixture_referee)s, %(fixture_timezone)s, %(fixture_date)s, %(fixture_timestamp)s,
            %(fixture_venue_id)s, %(fixture_venue_name)s, %(fixture_venue_city)s,
            %(fixture_status_long)s, %(fixture_status_short)s, %(fixture_status_elapsed)s,
            %(league_id)s, %(league_name)s, %(league_country)s, %(league_logo)s, %(league_flag)s, %(league_season)s, %(league_round)s,
            %(teams_home_id)s, %(teams_home_name)s, %(teams_home_logo)s, %(teams_home_winner)s,
            %(teams_away_id)s, %(teams_away_name)s, %(teams_away_logo)s, %(teams_away_winner)s,
            %(goals_home)s, %(goals_away)s,
            %(score_halftime_home)s, %(score_halftime_away)s,
            %(score_fulltime_home)s, %(score_fulltime_away)s,
            %(score_extratime_home)s, %(score_extratime_away)s,
            %(score_penalty_home)s, %(score_penalty_away)s,
            %(raw_data)s
        )
        ON CONFLICT (fixture_id) DO UPDATE SET
            fixture_referee = EXCLUDED.fixture_referee,
            fixture_status_long = EXCLUDED.fixture_status_long,
            fixture_status_short = EXCLUDED.fixture_status_short,
            fixture_status_elapsed = EXCLUDED.fixture_status_elapsed,
            goals_home = EXCLUDED.goals_home,
            goals_away = EXCLUDED.goals_away,
            score_halftime_home = EXCLUDED.score_halftime_home,
            score_halftime_away = EXCLUDED.score_halftime_away,
            score_fulltime_home = EXCLUDED.score_fulltime_home,
            score_fulltime_away = EXCLUDED.score_fulltime_away,
            score_extratime_home = EXCLUDED.score_extratime_home,
            score_extratime_away = EXCLUDED.score_extratime_away,
            score_penalty_home = EXCLUDED.score_penalty_home,
            score_penalty_away = EXCLUDED.score_penalty_away,
            raw_data = EXCLUDED.raw_data,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        try:
            with self.connection.cursor() as cursor:
                saved_count = 0
                updated_count = 0
                
                for fixture in fixtures_data:
                    # 提取数据
                    fixture_data = {
                        'fixture_id': fixture['fixture']['id'],
                        'fixture_referee': fixture['fixture'].get('referee'),
                        'fixture_timezone': fixture['fixture'].get('timezone'),
                        'fixture_date': fixture['fixture'].get('date'),
                        'fixture_timestamp': fixture['fixture'].get('timestamp'),
                        'fixture_venue_id': fixture['fixture']['venue'].get('id') if fixture['fixture'].get('venue') else None,
                        'fixture_venue_name': fixture['fixture']['venue'].get('name') if fixture['fixture'].get('venue') else None,
                        'fixture_venue_city': fixture['fixture']['venue'].get('city') if fixture['fixture'].get('venue') else None,
                        'fixture_status_long': fixture['fixture']['status'].get('long'),
                        'fixture_status_short': fixture['fixture']['status'].get('short'),
                        'fixture_status_elapsed': fixture['fixture']['status'].get('elapsed'),
                        'league_id': fixture['league']['id'],
                        'league_name': fixture['league'].get('name'),
                        'league_country': fixture['league'].get('country'),
                        'league_logo': fixture['league'].get('logo'),
                        'league_flag': fixture['league'].get('flag'),
                        'league_season': fixture['league'].get('season'),
                        'league_round': fixture['league'].get('round'),
                        'teams_home_id': fixture['teams']['home']['id'],
                        'teams_home_name': fixture['teams']['home'].get('name'),
                        'teams_home_logo': fixture['teams']['home'].get('logo'),
                        'teams_home_winner': fixture['teams']['home'].get('winner'),
                        'teams_away_id': fixture['teams']['away']['id'],
                        'teams_away_name': fixture['teams']['away'].get('name'),
                        'teams_away_logo': fixture['teams']['away'].get('logo'),
                        'teams_away_winner': fixture['teams']['away'].get('winner'),
                        'goals_home': fixture['goals']['home'],
                        'goals_away': fixture['goals']['away'],
                        'score_halftime_home': fixture['score']['halftime'].get('home') if fixture['score'].get('halftime') else None,
                        'score_halftime_away': fixture['score']['halftime'].get('away') if fixture['score'].get('halftime') else None,
                        'score_fulltime_home': fixture['score']['fulltime'].get('home') if fixture['score'].get('fulltime') else None,
                        'score_fulltime_away': fixture['score']['fulltime'].get('away') if fixture['score'].get('fulltime') else None,
                        'score_extratime_home': fixture['score']['extratime'].get('home') if fixture['score'].get('extratime') else None,
                        'score_extratime_away': fixture['score']['extratime'].get('away') if fixture['score'].get('extratime') else None,
                        'score_penalty_home': fixture['score']['penalty'].get('home') if fixture['score'].get('penalty') else None,
                        'score_penalty_away': fixture['score']['penalty'].get('away') if fixture['score'].get('penalty') else None,
                        'raw_data': json.dumps(fixture)
                    }
                    
                    # 检查记录是否已存在
                    cursor.execute("SELECT fixture_id FROM fixtures WHERE fixture_id = %s", (fixture_data['fixture_id'],))
                    exists = cursor.fetchone()
                    
                    # 执行插入或更新
                    cursor.execute(insert_sql, fixture_data)
                    
                    if exists:
                        updated_count += 1
                    else:
                        saved_count += 1
                
                logger.info(f"数据保存完成: 新增 {saved_count} 条，更新 {updated_count} 条")
                return True
                
        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}")
            return False
    
    def get_and_save_fixtures_by_date(self, date_str: str = None) -> bool:
        """
        获取某一天的fixture数据并存入数据库
        
        参数:
            date_str: 日期字符串，格式为YYYY-MM-DD，默认为当天
        
        返回:
            bool: 操作是否成功
        """
        try:
            # 确保数据库连接
            if not self.connection:
                if not self.connect_db():
                    return False
            
            # 确保表存在
            if not self.create_fixtures_table():
                return False
            
            # 获取数据
            fixtures_data = self.get_fixtures_by_date(date_str)
            if fixtures_data is None:
                return False
            
            # 保存数据
            return self.save_fixtures_to_db(fixtures_data)
            
        except Exception as e:
            logger.error(f"获取并保存fixture数据失败: {e}")
            return False
    
    def get_fixtures_from_db(self, date_str: str = None, league_id: int = None) -> Optional[List[Dict]]:
        """
        从数据库获取fixture数据
        
        参数:
            date_str: 日期字符串，格式为YYYY-MM-DD
            league_id: 联赛ID
        
        返回:
            List[Dict]: 比赛数据列表
        """
        if not self.connection:
            if not self.connect_db():
                return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                sql = "SELECT * FROM fixtures WHERE 1=1"
                params = []
                
                if date_str:
                    sql += " AND DATE(fixture_date) = %s"
                    params.append(date_str)
                
                if league_id:
                    sql += " AND league_id = %s"
                    params.append(league_id)
                
                sql += " ORDER BY fixture_date"
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"从数据库获取数据失败: {e}")
            return None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect_db()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect_db()


# 使用示例
if __name__ == "__main__":
    print("=== API-Football 数据保存工具 ===")
    print("按参数指定时区与日期，获取并保存当日比赛")
    print()

    parser = argparse.ArgumentParser(description="获取指定日期和时区的比赛数据并保存到PostgreSQL")
    parser.add_argument("-d", "--date", help="日期，格式 YYYY-MM-DD；默认今天", default=None)
    parser.add_argument("-t", "--timezone", help="时区（例如 Asia/Singapore），默认 UTC", default="UTC")
    args = parser.parse_args()

    # 处理日期参数（默认今天）
    if args.date:
        try:
            datetime.datetime.strptime(args.date, "%Y-%m-%d")
            date_str = args.date
        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式（例如: 2025-01-24）")
            raise SystemExit(1)
    else:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        print(f"使用今天的日期: {date_str}")

    print()
    print(f"正在连接数据库并获取数据（时区: {args.timezone}）...")

    try:
        with DataSaver(timezone=args.timezone) as saver:
            success = saver.get_and_save_fixtures_by_date(date_str)
            if success:
                print("✅ 数据获取并保存成功")
                fixtures = saver.get_fixtures_from_db(date_str=date_str)
                if fixtures:
                    print(f"📊 从数据库查询到 {len(fixtures)} 条比赛记录")
                    print("\n--- 比赛信息预览 ---")
                    for i, fixture in enumerate(fixtures[:5]):
                        home_team = fixture.get('teams_home_name', 'Unknown')
                        away_team = fixture.get('teams_away_name', 'Unknown')
                        league_name = fixture.get('league_name', 'Unknown')
                        status = fixture.get('fixture_status_long', 'Unknown')
                        print(f"{i+1}. {home_team} vs {away_team} ({league_name}) - {status}")
                    if len(fixtures) > 5:
                        print(f"... 还有 {len(fixtures) - 5} 场比赛")
                else:
                    print("⚠️  数据库查询失败或无数据")
            else:
                print("❌ 数据获取或保存失败")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

    print("\n程序执行完成，按任意键退出...")
    input()