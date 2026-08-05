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
    # ① 魚のマスタデータをロード
    json_path = os.path.join(base_dir, "jsonall", "fishes.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_fishes = json.load(f)

    # ② 魚とサイズを決定
    fish_names = list(all_fishes.keys())
    chosen_name = random.choice(fish_names)
    fish_data = all_fishes[chosen_name]
    size = random.randint(fish_data["min_size"], fish_data["max_size"])

    # ③ コメント取得
    comment = "コメントが見つかりませんでした"
    for item in fish_data["comments"]:
        if item["min"] <= size <= item["max"]:
            comment = item["text"]
            break

    # ④ ユーザーデータの更新
    user_id = str(ctx.author.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {"name": ctx.author.name, "inventory": {}}

    inventory = users_data[user_id]["inventory"]

    # 初めて釣る魚の場合の初期化
    if chosen_name not in inventory:
        inventory[chosen_name] = {"count": 0, "max_size": 0}

    # 個数を+1
    inventory[chosen_name]["count"] += 1

    # 自己ベスト更新判定！
    is_new_record = False
    if size > inventory[chosen_name]["max_size"]:
        inventory[chosen_name]["max_size"] = size
        is_new_record = True

    # 保存
    save_user_data(users_data)

    # メッセージの組み立て
    record_text = " 👑 **自己ベスト更新！**" if is_new_record else ""
    await ctx.send(
        f"🎣 **{chosen_name}（{size}cm）** を釣り上げた！{record_text}\n"
        f"{comment}\n"
        f"📦（通算: {inventory[chosen_name]['count']}匹 / 最大: {inventory[chosen_name]['max_size']}cm）"
    )
@bot.command(aliases=["inv", "bag"])
async def inventory(ctx):
    """自分の所持している魚と最高記録を表示する"""
    user_id = str(ctx.author.id)
    users_data = load_user_data()

    # データが無い、またはインベントリが空の場合
    if (
        user_id not in users_data
        or not users_data[user_id].get("inventory")
    ):
        await ctx.send(
            f"📦 **{ctx.author.display_name}** さんのバッグは空っぽです！`!fish` で魚を釣りましょう！"
        )
        return

    user_inventory = users_data[user_id]["inventory"]

    # 表示用テキストの組み立て
    msg = f"📦 **{ctx.author.display_name} さんの魚バッグ・図鑑** 📦\n"
    msg += "───────────────────\n"

    for fish_name, data in user_inventory.items():
        count = data.get("count", 0)
        max_size = data.get("max_size", 0)
        msg += f"🐟 **{fish_name}**: {count}匹 （最大: {max_size}cm）\n"

    msg += "───────────────────"

    await ctx.send(msg)

bot.run(TOKEN)