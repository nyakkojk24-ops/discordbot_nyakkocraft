import os
import json
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

base_dir = os.path.dirname(__file__)

bot = commands.Bot(command_prefix="!", intents=intents)

# 保存先のパスを設定（main.py と同じ場所にある data/users.json）
users_json_path = os.path.join(base_dir, "data", "users.json")


# ① ユーザーデータを読み込む関数
def load_user_data():
    """users.json を読み込む（ファイルが無ければ空のデータを返す）"""
    if not os.path.exists(users_json_path):
        return {}
    with open(users_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ② ユーザーデータを保存する関数
def save_user_data(data):
    """users.json にデータを保存する"""
    # data フォルダが存在しない場合は自動で作る
    data_dir = os.path.dirname(users_json_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # "w" モードで書き込み保存！
    with open(users_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bot.command()
async def fish(ctx):
    json_path = os.path.join(base_dir, "jsonall", "fishes.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_fishes = json.load(f)

    fish_names = list(all_fishes.keys())
    chosen_name = random.choice(fish_names)
    fish_data = all_fishes[chosen_name]
    size = random.randint(fish_data["min_size"], fish_data["max_size"])

    comment = "コメントが見つかりませんでした"
    for item in fish_data["comments"]:
        if item["min"] <= size <= item["max"]:
            comment = item["text"]
            break

    user_id = str(ctx.author.id)  # コマンドを打った人のDiscord ID
    users_data = load_user_data()  # 今の全ユーザーデータを取得

    # 初めてコマンドを打った人なら初期化
    if user_id not in users_data:
        users_data[user_id] = {"name": ctx.author.name, "inventory": {}}

    # インベントリを取得
    inventory = users_data[user_id]["inventory"]

    # すでに持っている魚なら +1、持ってないなら 1 個にする
    inventory[chosen_name] = inventory.get(chosen_name, 0) + 1

    # 最新データをファイルに保存！
    save_user_data(users_data)

    count = inventory[chosen_name]
    await ctx.send(
        f"🎣 **{chosen_name}（{size}cm）** を釣り上げた！\n"
        f"{comment}\n"
        f"📦（現在の所持数: {count}匹）"
    )

bot.run(TOKEN)