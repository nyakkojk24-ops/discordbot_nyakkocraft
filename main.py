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


class InventoryView(discord.ui.View):

    def __init__(self, author, user_inventory):
        super().__init__(timeout=60)  # 60秒でボタンを無効化する
        self.author = author
        self.user_inventory = user_inventory

    # 1つ目のボタン：魚の一覧
    @discord.ui.button(
        label="🐟 魚一覧", style=discord.ButtonStyle.primary
    )
    async def show_fishes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # ボタンを押した人がコマンド実行者本人かチェック
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        # 魚一覧のテキストを作成
        msg = f"📦 **{self.author.display_name} さんの魚バッグ** 📦\n"
        msg += "───────────────────\n"

        if not self.user_inventory:
            msg += "魚を持っていません！\n"
        else:
            for fish_name, data in self.user_inventory.items():
                count = data.get("count", 0)
                max_size = data.get("max_size", 0)
                msg += f"🐟 **{fish_name}**: {count}匹 （最大: {max_size}cm）\n"

        msg += "───────────────────"

        # メッセージを更新！
        await interaction.response.edit_message(content=msg, view=self)

    # 2つ目のボタン：料理一覧（将来の準備！）
    @discord.ui.button(
        label="🍳 料理一覧", style=discord.ButtonStyle.secondary
    )
    async def show_dishes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        msg = f"🍳 **{self.author.display_name} さんの料理バッグ** 🍳\n"
        msg += "───────────────────\n"
        msg += "まだ料理を持っていません！（次回実装予定！）\n"
        msg += "───────────────────"

        await interaction.response.edit_message(content=msg, view=self)


# --------------------------------------------------
# 📦 インベントリ確認コマンド
# --------------------------------------------------
@bot.command(aliases=["inv", "bag"])
async def inventory(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()

    user_inventory = users_data.get(user_id, {}).get("inventory", {})

    # 最初に見せる画面（初期表示）
    msg = f"📦 **{ctx.author.display_name} さんのインベントリ** 📦\n"
    msg += "下のボタンを押して「魚一覧」や「料理一覧」に切り替えられます！"

    # View（ボタン群）を生成してメッセージと一緒に送信！
    view = InventoryView(author=ctx.author, user_inventory=user_inventory)
    await ctx.send(msg, view=view)