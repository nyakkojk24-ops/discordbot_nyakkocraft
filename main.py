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

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command()
async def fish(ctx):
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "jsonall", "fishes.json")
    # ① 全魚のデータをロード
    with open(json_path, "r", encoding="utf-8") as f:
        all_fishes = json.load(f)  

    # ② 魚の名前のリスト ["マグロ", "アジ"] を作成
    fish_names = list(all_fishes.keys())

    # ③ ランダムで1つ選ぶ（例: "マグロ"）
    chosen_name = random.choice(fish_names)

    # ④ 選ばれた魚のデータを取り出す
    fish_data = all_fishes[chosen_name]

    # ⑤ サイズ（数値）をランダム決定
    size = random.randint(fish_data["min_size"], fish_data["max_size"])

    # ⑥ サイズに合ったコメントを探す
    comment = "コメントが見つかりませんでした"

    for item in fish_data["comments"]:
        if item["min"] <= size <= item["max"]:
            # 【ここが穴埋め問題！】
            # JSONの { "min": 100, "max": 109, "text": "〜" } の中から「文章」を取り出したい！
            comment = item["text"]
            break

    await ctx.send(f"🎣 **{chosen_name}（{size}cm）** を釣り上げた！\n{comment}")

bot.run(TOKEN)