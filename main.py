import json
import os
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

# 保存先のパスを設定
users_json_path = os.path.join(base_dir, "data", "users.json")
recipes_json_path = os.path.join(base_dir, "data", "recipes.json")


# --------------------------------------------------
# 📁 データの読み書き関数
# --------------------------------------------------
def load_recipes():
    """recipes.json を読み込む"""
    if not os.path.exists(recipes_json_path):
        return {}
    with open(recipes_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recipes(data):
    """recipes.json にデータを保存する"""
    data_dir = os.path.dirname(recipes_json_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    with open(recipes_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_user_data():
    """users.json を読み込む"""
    if not os.path.exists(users_json_path):
        return {}
    with open(users_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user_data(data):
    """users.json にデータを保存する"""
    data_dir = os.path.dirname(users_json_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    with open(users_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------------------------------
# 🖼️ UIクラス群（Modal & View）
# --------------------------------------------------


class ShowItemSelectView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

        inventory = user_data.get("inventory", {})
        dishes = user_data.get("dishes", {})

        options = []

        # 魚をお披露目対象に追加（sizes の長さで判定）
        for fish_name, data in inventory.items():
            sizes = data.get("sizes", [])
            if len(sizes) > 0:
                max_size = data.get("max_size", 0)
                options.append(
                    discord.SelectOption(
                        label=f"🐟 {fish_name} (最大: {max_size}cm)",
                        value=f"fish_{fish_name}",
                        description="最高記録のサイズでお披露目します！",
                    )
                )

        # 料理をお披露目対象に追加
        for dish_name, count in dishes.items():
            if count > 0:
                options.append(
                    discord.SelectOption(
                        label=f"🍳 {dish_name} ({count}個所持)",
                        value=f"dish_{dish_name}",
                        description="作成した自作料理をお披露目します！",
                    )
                )

        if options:
            select = discord.ui.Select(
                placeholder="📢 お披露目したいアイテムを選んでください",
                options=options[:25],
            )
            select.callback = self.on_select_item
            self.add_item(select)

    async def on_select_item(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "❌ ボイスチャンネル（VC）に参加した状態で実行してください！",
                ephemeral=True,
            )
            return

        vc_channel = voice_state.channel
        selected_val = interaction.data["values"][0]

        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(
            name=f"{self.author.display_name} さんの自慢の一品！",
            icon_url=(
                self.author.display_avatar.url
                if self.author.display_avatar
                else None
            ),
        )

        if selected_val.startswith("fish_"):
            fish_name = selected_val.replace("fish_", "")
            fish_info = self.user_data["inventory"][fish_name]
            max_size = fish_info.get("max_size", 0)
            count = len(fish_info.get("sizes", []))

            embed.title = f"🐟 魚自慢: 『{fish_name}』"
            embed.description = f"**最大サイズ: {max_size} cm** 👑\n（現在所持数: {count} 匹）"
            embed.set_footer(text="🎣 釣りあげた自慢の記録！")

        elif selected_val.startswith("dish_"):
            dish_name = selected_val.replace("dish_", "")
            recipes = load_recipes()

            author_name = "自作"
            appliance = "不明"
            ingredients = "不明"

            for key, dish_list in recipes.items():
                for dish in dish_list:
                    if dish["name"] == dish_name:
                        author_name = dish.get("author", "不明")
                        appliance = dish.get("appliance", "不明")
                        ingredients = ", ".join(dish.get("ingredients", []))
                        break

            embed.title = f"🍳 料理披露: 『{dish_name}』"
            embed.description = (
                f"**考案者:** {author_name}\n"
                f"**調理器具:** {appliance}\n"
                f"**材料:** {ingredients}"
            )
            embed.set_footer(text="✨ 特製料理をお披露目！")

        await vc_channel.send(embed=embed)
        await interaction.response.send_message(
            f"📢 **{vc_channel.name}** のチャットにお披露目しました！",
            ephemeral=True,
        )


# ① インベントリ画面（魚・料理一覧）
class InventoryView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

    @discord.ui.button(
        label="🐟 魚一覧", style=discord.ButtonStyle.primary, row=0
    )
    async def show_fishes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        inventory = self.user_data.get("inventory", {})
        msg = f"📦 **{self.author.display_name} さんの魚バッグ** 📦\n"
        msg += "───────────────────\n"

        has_item = False
        for fish_name, data in inventory.items():
            # sizes リストの長さで所持数を判定！
            sizes = data.get("sizes", [])
            count = len(sizes)
            max_size = data.get("max_size", 0)

            if count > 0:
                msg += f"🐟 **{fish_name}**: {count}匹 （最大: {max_size}cm）\n"
                has_item = True

        if not has_item:
            msg += "魚を持っていません！\n"

        msg += "───────────────────"
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(
        label="🍳 料理一覧", style=discord.ButtonStyle.secondary, row=0
    )
    async def show_dishes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        dishes = self.user_data.get("dishes", {})
        msg = f"🍳 **{self.author.display_name} さんの料理バッグ** 🍳\n"
        msg += "───────────────────\n"

        has_item = False
        for dish_name, count in dishes.items():
            if count > 0:
                msg += f"🍳 **{dish_name}**: {count}個\n"
                has_item = True

        if not has_item:
            msg += "まだ料理を持っていません！`!cook` で料理を作りましょう！\n"

        msg += "───────────────────"
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(
        label="📢 VCにお披露目", style=discord.ButtonStyle.success, row=1
    )
    async def share_to_vc(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "❌ お披露目するには、ボイスチャンネル（VC）に参加してください！",
                ephemeral=True,
            )
            return

        show_view = ShowItemSelectView(
            author=self.author, user_data=self.user_data
        )
        await interaction.response.send_message(
            "📢 VCに自慢したいアイテムを選んでください！",
            view=show_view,
            ephemeral=True,
        )


# ② 新料理の命名モーダル
class NameDishModal(discord.ui.Modal, title="🎉 新料理の命名！"):
    dish_name_input = discord.ui.TextInput(
        label="料理名を入力してください",
        placeholder="例：マグロの特製スムージー",
        max_length=30,
        required=True,
    )

    def __init__(self, recipe_key, appliance, selected_fishes, user):
        super().__init__()
        self.recipe_key = recipe_key
        self.appliance = appliance
        self.selected_fishes = selected_fishes
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        dish_name = self.dish_name_input.value.strip()

        recipes = load_recipes()
        if self.recipe_key not in recipes:
            recipes[self.recipe_key] = []

        new_dish = {
            "name": dish_name,
            "appliance": self.appliance,
            "ingredients": self.selected_fishes,
            "author": self.user.name,
        }
        recipes[self.recipe_key].append(new_dish)
        save_recipes(recipes)

        users_data = load_user_data()
        user_id = str(self.user.id)
        if "dishes" not in users_data[user_id]:
            users_data[user_id]["dishes"] = {}

        dishes = users_data[user_id]["dishes"]
        dishes[dish_name] = dishes.get(dish_name, 0) + 1
        save_user_data(users_data)

        await interaction.response.send_message(
            f"✨ **新レシピ『{dish_name}』を登録・作成しました！** 🎉\n"
            f"考案者: **{self.user.display_name}**\n"
            f"（調理器具: {self.appliance} / 材料: {', '.join(self.selected_fishes)}）"
        )


# ③ 既存レシピがある場合の選択画面
class SelectRecipeView(discord.ui.View):

    def __init__(
        self, author, recipe_key, existing_list, appliance, selected_fishes
    ):
        super().__init__(timeout=60)
        self.author = author
        self.recipe_key = recipe_key
        self.existing_list = existing_list
        self.appliance = appliance
        self.selected_fishes = selected_fishes

        options = [
            discord.SelectOption(
                label=dish["name"], description=f"考案者: {dish['author']}"
            )
            for dish in existing_list
        ]

        select = discord.ui.Select(
            placeholder="📜 既存のレシピから選んで作る", options=options
        )
        select.callback = self.on_select_existing
        self.add_item(select)

    async def on_select_existing(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return

        chosen_name = interaction.data["values"][0]

        users_data = load_user_data()
        user_id = str(self.author.id)
        if "dishes" not in users_data[user_id]:
            users_data[user_id]["dishes"] = {}

        dishes = users_data[user_id]["dishes"]
        dishes[chosen_name] = dishes.get(chosen_name, 0) + 1
        save_user_data(users_data)

        await interaction.response.send_message(
            f"🍳 **{self.appliance}** で調理完了！\n"
            f"✨ **『{chosen_name}』** が出来上がりました！"
        )

    @discord.ui.button(
        label="✨ 新しい料理名を考案して作る！",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def create_new_recipe(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        modal = NameDishModal(
            recipe_key=self.recipe_key,
            appliance=self.appliance,
            selected_fishes=self.selected_fishes,
            user=self.author,
        )
        await interaction.response.send_modal(modal)


# ④ 調理メイン画面
class CookingView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=120)
        self.author = author
        self.user_data = user_data
        self.selected_appliance = "ミキサー"
        self.selected_fishes = []

        user_inventory = user_data.get("inventory", {})
        user_dishes = user_data.get("dishes", {})

        # 調理器具の選択
        appliance_select = discord.ui.Select(
            placeholder="🍳 調理器具を選んでください（初期値: ミキサー）",
            options=[
                discord.SelectOption(
                    label="ミキサー",
                    description="細かくすりつぶしてペースト状にする",
                    emoji="🥣",
                ),
                discord.SelectOption(
                    label="フライパン",
                    description="じっくり焼いて香ばしく仕上げる",
                    emoji="🍳",
                ),
                discord.SelectOption(
                    label="鍋",
                    description="煮込んで出汁やスープを取る",
                    emoji="🍲",
                ),
                discord.SelectOption(
                    label="包丁",
                    description="切り分けて刺身やタタキにする",
                    emoji="🔪",
                ),
            ],
        )
        appliance_select.callback = self.on_appliance_select
        self.add_item(appliance_select)

        # 素材・料理の混合選択肢を作成
        ingredient_options = []

        for name, data in user_inventory.items():
            if data.get("count", 0) > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🐟 {name} ({data['count']}所持)",
                        value=name,
                    )
                )

        for name, count in user_dishes.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🍳 {name} ({count}個所持)", value=name
                    )
                )

        if ingredient_options:
            ingredient_select = discord.ui.Select(
                placeholder="🥗 材料を選んでください（組み合わせ自由！）",
                min_values=1,
                max_values=min(len(ingredient_options), 3),
                options=ingredient_options,
            )
            ingredient_select.callback = self.on_fish_select
            self.add_item(ingredient_select)

    async def on_appliance_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return
        self.selected_appliance = interaction.data["values"][0]
        await interaction.response.send_message(
            f"調理器具を **{self.selected_appliance}** にセットしました！",
            ephemeral=True,
        )

    async def on_fish_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return
        self.selected_fishes = interaction.data["values"]
        await interaction.response.send_message(
            f"材料に **{', '.join(self.selected_fishes)}** を選びました！",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🔥 調理スタート！",
        style=discord.ButtonStyle.success,
        row=2,
    )
    async def start_cooking(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        if not self.selected_fishes:
            await interaction.response.send_message(
                "材料（魚または料理）を1つ以上選択してください！",
                ephemeral=True,
            )
            return

        users_data = load_user_data()
        user_id = str(self.author.id)
        user = users_data.get(user_id, {})
        inventory = user.get("inventory", {})
        dishes = user.get("dishes", {})

        # 1. 在庫チェック
        for item in self.selected_fishes:
            fish_count = inventory.get(item, {}).get("count", 0)
            dish_count = dishes.get(item, 0)

            if fish_count <= 0 and dish_count <= 0:
                await interaction.response.send_message(
                    f"**{item}** の在庫が足りません！", ephemeral=True
                )
                return

        # 2. 消費処理
        for item in self.selected_fishes:
            if inventory.get(item, {}).get("count", 0) > 0:
                inventory[item]["count"] -= 1
            elif dishes.get(item, 0) > 0:
                dishes[item] -= 1

        save_user_data(users_data)

        # 3. レシピ判定
        sorted_fishes = sorted(self.selected_fishes)
        recipe_key = (
            f"{self.selected_appliance}_" + "_".join(sorted_fishes)
        )
        recipes = load_recipes()

        if recipe_key in recipes and len(recipes[recipe_key]) > 0:
            select_view = SelectRecipeView(
                author=self.author,
                recipe_key=recipe_key,
                existing_list=recipes[recipe_key],
                appliance=self.selected_appliance,
                selected_fishes=self.selected_fishes,
            )
            await interaction.response.send_message(
                "💡 この組み合わせのレシピがすでに存在します！\n"
                "既存の料理を作るか、新しく料理名を考案するか選んでください！",
                view=select_view,
            )
        else:
            modal = NameDishModal(
                recipe_key=recipe_key,
                appliance=self.selected_appliance,
                selected_fishes=self.selected_fishes,
                user=self.author,
            )
            await interaction.response.send_modal(modal)

# --------------------------------------------------
# 🐟 40cm以下の場合のキープ / リリース選択画面
# --------------------------------------------------
class CatchOrReleaseView(discord.ui.View):

    def __init__(
        self, author, fish_name, size, comment, is_new_record, users_data
    ):
        super().__init__(timeout=30)
        self.author = author
        self.fish_name = fish_name
        self.size = size
        self.comment = comment
        self.is_new_record = is_new_record
        self.users_data = users_data

    @discord.ui.button(
        label="📦 持ち帰る", style=discord.ButtonStyle.primary
    )
    async def keep_fish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        user_id = str(self.author.id)
        inventory = self.users_data[user_id]["inventory"]

        if self.fish_name not in inventory:
            inventory[self.fish_name] = {"sizes": [], "max_size": 0}

        # 互換性維持（もし旧データで sizes が無ければ空リストで初期化）
        if "sizes" not in inventory[self.fish_name]:
            inventory[self.fish_name]["sizes"] = []

        # サイズをリストに追加！
        inventory[self.fish_name]["sizes"].append(self.size)

        if self.size > inventory[self.fish_name]["max_size"]:
            inventory[self.fish_name]["max_size"] = self.size

        save_user_data(self.users_data)

        count = len(inventory[self.fish_name]["sizes"])
        record_text = " 👑 **自己ベスト更新！**" if self.is_new_record else ""
        msg = (
            f"📦 **{self.fish_name}（{self.size}cm）** を持ち帰りました！{record_text}\n"
            f"（所持数: {count}匹 / 最大記録: {inventory[self.fish_name]['max_size']}cm）"
        )
        self.stop()
        await interaction.response.edit_message(content=msg, view=None)

    @discord.ui.button(
        label="🌊 逃がす（リリース）",
        style=discord.ButtonStyle.secondary,
    )
    async def release_fish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        msg = f"🌊 **{self.fish_name}（{self.size}cm）** を海に逃がしてあげた！「大きくなって戻ってこいよ〜！」"
        self.stop()
        await interaction.response.edit_message(content=msg, view=None)

# --------------------------------------------------
# 💰 魚・料理の売却画面（View）
# --------------------------------------------------
class SellView(discord.ui.View):

    def __init__(self, author, user_data, all_fishes):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data
        self.all_fishes = all_fishes

        inventory = user_data.get("inventory", {})
        options = []

        # 魚を売却選択肢に追加（サイズに応じて価格計算！）
        for fish_name, data in inventory.items():
            count = data.get("count", 0)
            if count > 0 and fish_name in all_fishes:
                fish_master = all_fishes[fish_name]
                max_size = data.get("max_size", fish_master["min_size"])

                # 価格計算ロジック
                base_price = fish_master.get("base_price", 100)  # デフォルト100NP
                min_size = fish_master["min_size"]
                # 10cmごとに+20NP追加
                extra_price = int((max_size - min_size) / 10) * 20
                unit_price = base_price + extra_price

                options.append(
                    discord.SelectOption(
                        label=f"🐟 {fish_name} (所持: {count}匹)",
                        value=fish_name,
                        description=f"最高記録 {max_size}cm 基準 ➔ 1匹 {unit_price} NP で売却",
                    )
                )

        if options:
            select = discord.ui.Select(
                placeholder="💰 売却したい魚を選んでください（1匹ずつ売却）",
                options=options[:25],
            )
            select.callback = self.on_select_sell
            self.add_item(select)

    async def on_select_sell(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return

        chosen_fish = interaction.data["values"][0]

        users_data = load_user_data()
        user_id = str(self.author.id)
        user = users_data.get(user_id, {})
        inventory = user.get("inventory", {})

        if inventory.get(chosen_fish, {}).get("count", 0) <= 0:
            await interaction.response.send_message(
                "その魚はもう持っていません！", ephemeral=True
            )
            return

        # 売却価格の再計算
        fish_master = self.all_fishes[chosen_fish]
        max_size = inventory[chosen_fish].get(
            "max_size", fish_master["min_size"]
        )
        base_price = fish_master.get("base_price", 100)
        min_size = fish_master["min_size"]
        extra_price = int((max_size - min_size) / 10) * 20
        unit_price = base_price + extra_price

        # 在庫を1減らし、NPを付与
        inventory[chosen_fish]["count"] -= 1
        user["coins"] = user.get("coins", 0) + unit_price

        save_user_data(users_data)

        await interaction.response.send_message(
            f"💸 **{chosen_fish}（最大{max_size}cm記録）** を1匹売却しました！\n"
            f"💰 **+{unit_price} NP** を獲得！（現在の所持金: **{user['coins']} NP**）"
        ) 




# --------------------------------------------------
# 🤖 BOTコマンド群
# --------------------------------------------------


# 1. インベントリ確認コマンド
@bot.command(aliases=["inv", "bag"])
async def inventory(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()
    user_data = users_data.get(user_id, {})

    msg = f"📦 **{ctx.author.display_name} さんのインベントリ** 📦\n"
    msg += "下のボタンを押して「魚一覧」や「料理一覧」に切り替えられます！"

    view = InventoryView(author=ctx.author, user_data=user_data)
    await ctx.send(msg, view=view)


# 2. 釣りコマンド
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

    user_id = str(ctx.author.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": ctx.author.name,
            "coins": 100,  # 初期コイン
            "inventory": {},
            "dishes": {},
        }

    inventory = users_data[user_id]["inventory"]

    current_max = inventory.get(chosen_name, {}).get("max_size", 0)
    is_new_record = size > current_max

    # 40cm以下の場合は選択ボタンを出す
    if size <= 40:
        view = CatchOrReleaseView(
            author=ctx.author,
            fish_name=chosen_name,
            size=size,
            comment=comment,
            is_new_record=is_new_record,
            users_data=users_data,
        )
        await ctx.send(
            f"🎣 **{chosen_name}（{size}cm）** が釣れた！\n"
            f"{comment}\n"
            f"⚠️ **40cm以下の小魚です！どうする？**",
            view=view,
        )

    # 40cm超えの場合はそのまま自動持ち帰り
    else:
        if chosen_name not in inventory:
            inventory[chosen_name] = {"sizes": [], "max_size": 0}

        if "sizes" not in inventory[chosen_name]:
            inventory[chosen_name]["sizes"] = []

        inventory[chosen_name]["sizes"].append(size)

        if is_new_record:
            inventory[chosen_name]["max_size"] = size

        save_user_data(users_data)

        count = len(inventory[chosen_name]["sizes"])
        record_text = " 👑 **自己ベスト更新！**" if is_new_record else ""
        await ctx.send(
            f"🎣 **{chosen_name}（{size}cm）** を釣り上げた！{record_text}\n"
            f"{comment}\n"
            f"📦（所持数: {count}匹 / 最大記録: {inventory[chosen_name]['max_size']}cm）"
        )



# 3. 料理コマンド
@bot.command(aliases=["cook", "料理"])
async def cooking(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()

    user_data = users_data.get(user_id, {})
    user_inventory = user_data.get("inventory", {})
    user_dishes = user_data.get("dishes", {})

    has_fish = any(
        data.get("count", 0) > 0 for data in user_inventory.values()
    )
    has_dish = any(count > 0 for count in user_dishes.values())

    if not has_fish and not has_dish:
        await ctx.send(
            "🍳 調理に使える素材や料理を持っていません！まずは `!fish` で魚を釣りましょう！"
        )
        return

    view = CookingView(author=ctx.author, user_data=user_data)
    await ctx.send("🍳 **クッキングタイム！** 器具と材料を選んでね！", view=view)


# 4. レシピ図鑑コマンド
@bot.command(aliases=["recipes", "レシピ"])
async def recipe_book(ctx):
    recipes = load_recipes()

    if not recipes:
        await ctx.send(
            "📖 **レシピ図鑑** はまだ空っぽです！`!cook` で新しい料理を発見しましょう！"
        )
        return

    msg = "📖 **みんなのレシピ図鑑（発見済み料理一覧）** 📖\n"
    msg += "───────────────────\n"

    for key, dish_list in recipes.items():
        for dish in dish_list:
            name = dish["name"]
            author = dish.get("author", "不明")
            appliance = dish.get("appliance", "不明")
            ingredients = ", ".join(dish.get("ingredients", []))

            msg += f"🍳 **{name}** （考案者: {author}）\n"
            msg += f" └ 器具: {appliance} / 材料: {ingredients}\n"

    msg += "───────────────────"

    if len(msg) > 2000:
        await ctx.send(
            "📖 レシピが多いため、一部のみ表示します！\n" + msg[:1800] + "..."
        )
    else:
        await ctx.send(msg)


# --------------------------------------------------
# 💰 魚の売却画面（View）
# --------------------------------------------------
class SellView(discord.ui.View):

    def __init__(self, author, user_data, all_fishes):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data
        self.all_fishes = all_fishes

        inventory = user_data.get("inventory", {})
        options = []

        # 魚ごとに、持っている個別のサイズを計算して選択肢に追加
        for fish_name, data in inventory.items():
            sizes = data.get("sizes", [])
            if sizes and fish_name in all_fishes:
                fish_master = all_fishes[fish_name]
                base_price = fish_master.get("base_price", 100)
                min_size = fish_master["min_size"]

                # 個別のサイズごとに値段を計算
                for idx, size in enumerate(sizes):
                    extra_price = int((size - min_size) / 10) * 20
                    price = base_price + extra_price

                    # ドロップダウンで識別できるように value にインデックス(idx)を含める
                    options.append(
                        discord.SelectOption(
                            label=f"🐟 {fish_name} ({size}cm)",
                            value=f"{fish_name}_{idx}_{size}",
                            description=f"売却価格: {price} NP",
                        )
                    )

        if options:
            select = discord.ui.Select(
                placeholder="💰 売却したい魚（サイズ別）を選んでください",
                options=options[:25],  # 最大25個まで
            )
            select.callback = self.on_select_sell
            self.add_item(select)

    async def on_select_sell(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return

        # "マグロ_0_150" のような値から情報を分解
        val_parts = interaction.data["values"][0].split("_")
        chosen_fish = val_parts[0]
        fish_idx = int(val_parts[1])
        fish_size = int(val_parts[2])

        users_data = load_user_data()
        user_id = str(self.author.id)
        user = users_data.get(user_id, {})
        inventory = user.get("inventory", {})

        sizes = inventory.get(chosen_fish, {}).get("sizes", [])

        # 指定インデックスの魚がまだあるか確認
        if fish_idx >= len(sizes) or sizes[fish_idx] != fish_size:
            await interaction.response.send_message(
                "その魚はすでに売却されたか、見つかりません！",
                ephemeral=True,
            )
            return

        # 価格計算
        fish_master = self.all_fishes[chosen_fish]
        base_price = fish_master.get("base_price", 100)
        min_size = fish_master["min_size"]
        extra_price = int((fish_size - min_size) / 10) * 20
        unit_price = base_price + extra_price

        # リストから指定の魚を1匹削除 & コイン（NP）付与
        sizes.pop(fish_idx)
        user["coins"] = user.get("coins", 0) + unit_price

        save_user_data(users_data)

        await interaction.response.send_message(
            f"💸 **{chosen_fish}（{fish_size}cm）** を売却しました！\n"
            f"💰 **+{unit_price} NP** 獲得！（現在の所持金: **{user['coins']} NP**）"
        )


# --------------------------------------------------
# 💰 売却コマンド
# --------------------------------------------------
@bot.command(aliases=["sell", "売却"])
async def sell_item(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()
    user_data = users_data.get(user_id, {})

    inventory = user_data.get("inventory", {})
    has_fish = any(len(data.get("sizes", [])) > 0 for data in inventory.values())

    if not has_fish:
        await ctx.send(
            "💰 売れる魚を持っていません！まずは `!fish` で魚を釣りましょう！"
        )
        return

    json_path = os.path.join(base_dir, "jsonall", "fishes.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_fishes = json.load(f)

    coins = user_data.get("coins", 0)
    view = SellView(
        author=ctx.author, user_data=user_data, all_fishes=all_fishes
    )
    await ctx.send(
        f"🏧 **フィッシュマーケット**（現在の所持金: **{coins} NP**）\n"
        f"サイズが大きい魚ほど高額で引き取ります！売却したい魚を選んでね！",
        view=view,
    )


bot.run(TOKEN)