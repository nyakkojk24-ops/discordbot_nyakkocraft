import json
import os
import datetime
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


# 🌟 ここに meats.json 読み込み関数を追加！
def load_meats():
    """meats.json を読み込む"""
    json_path = os.path.join(base_dir, "jsonall", "meats.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_seafood():
    """seafood.json を読み込む"""
    json_path = os.path.join(base_dir, "jsonall", "seafood.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_daily_quest(user_data):
    today_str = datetime.date.today().isoformat()
    quest_info = user_data.get("daily_quest", {})

    # 1. 発見済みレシピ（recipes.json）を読み込む
    recipes = load_recipes()  # 既存のレシピ読み込み関数
    discovered_recipes = list(recipes.keys())

    # 2. レシピが10種類未満の場合は「ロック状態」を返す
    if len(discovered_recipes) < 10:
        return {
            "locked": True,
            "count": len(discovered_recipes),
            "needed": 10,
        }

    # 3. 10種類以上ある場合は、今日の日付でデイリークエストを生成
    if quest_info.get("date") != today_str or quest_info.get("locked"):
        # 今日の日付を固定シードにするか、ランダムに1つのレシピを選択
        # ユーザーIDと日付を組み合わせることで「ユーザーごとに今日固定のレシピ」を選出
        seed_value = f"{today_str}_{user_data.get('name', '')}"
        rng = random.Random(seed_value)

        target_recipe = rng.choice(discovered_recipes)
        recipe_data = recipes[target_recipe]

        # 報酬額の計算（食材数に応じたボーナスなどアレンジ可能！）
        reward = 250

        quest_info = {
            "locked": False,
            "date": today_str,
            "completed": False,
            "quest": {
                "item": target_recipe,
                "count": 1,
                "reward_coins": reward,
                "description": f"みんなが発見した『{target_recipe}』が食べたいにゃ！1個作って届けてほしいにゃ！",
            },
        }
        user_data["daily_quest"] = quest_info

    return quest_info



# 🥗 収穫処理の共通ロジック
async def do_farm_logic(interaction: discord.Interaction):
    json_path = os.path.join(base_dir, "jsonall", "crops.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_veggies = json.load(f)

    chosen_veggie = random.choice(list(all_veggies.keys()))
    veggie_info = all_veggies[chosen_veggie]

    user_id = str(interaction.user.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": interaction.user.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "dishes": {},
        }

    user = users_data[user_id]
    if "veggies" not in user:
        user["veggies"] = {}

    user["veggies"][chosen_veggie] = user["veggies"].get(chosen_veggie, 0) + 1
    save_user_data(users_data)

    await interaction.response.send_message(
        f"🥗 **{chosen_veggie}** を収穫した！\n💬 {veggie_info.get('description', '')}\n📦（所持数: {user['veggies'][chosen_veggie]}個）"
    )

# --------------------------------------------------
# 🎣 耐久値対応版：釣りロジック
# --------------------------------------------------
async def do_fish_logic_edit(
    interaction: discord.Interaction, view: discord.ui.View
):
    user_id = str(interaction.user.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": interaction.user.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "dishes": {},
            "durability": {"fishing_rod": 10, "hoe": 10},  # 初期耐久値（10回）
        }

    user = users_data[user_id]
    # 耐久値データがない既存ユーザー向けの互換処理
    if "durability" not in user:
        user["durability"] = {"fishing_rod": 10, "hoe": 10}

    # 🪓 耐久値チェック
    rod_durability = user["durability"].get("fishing_rod", 0)
    if rod_durability <= 0:
        await interaction.response.edit_message(
            content=(
                "💥 **釣竿が壊れています！**\n"
                "ショップや修理コマンドで新しい釣竿を手に入れてね！\n\n"
                "👇 **メニューに戻る**"
            ),
            embed=None,
            view=view,
        )
        return

    # 耐久値を 1 減らす
    user["durability"]["fishing_rod"] -= 1
    current_rod = user["durability"]["fishing_rod"]

    # --- 🐟 以下、既存の釣り判定処理 ---
    json_path = os.path.join(base_dir, "jsonall", "fishes.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_fishes = json.load(f)

    chosen_name = random.choice(list(all_fishes.keys()))
    fish_data = all_fishes[chosen_name]
    raw_size = random.uniform(fish_data["min_size"], fish_data["max_size"])
    size = round(raw_size, 2)

    comment = "コメントが見つかりませんでした"
    for item in fish_data["comments"]:
        if item["min"] <= size <= item["max"]:
            comment = item["text"]
            break

    inventory = user["inventory"]
    current_max = inventory.get(chosen_name, {}).get("max_size", 0)
    is_new_record = size > current_max

    # 壊れた瞬間の警告テキスト
    broke_text = "\n⚠️ **釣竿が壊れてしまった！**" if current_rod == 0 else ""

    if size <= 40:
        catch_view = CatchOrReleaseView(
            author=interaction.user,
            fish_name=chosen_name,
            size=size,
            comment=comment,
            is_new_record=is_new_record,
            users_data=users_data,
        )
        await interaction.response.edit_message(
            content=(
                f"🎣 **{chosen_name}（{size:.2f}cm）** が釣れた！\n"
                f"{comment}\n"
                f"🛠️ (釣竿残り耐久: {current_rod}){broke_text}\n"
                f"⚠️ **40cm以下の小魚です！どうする？**"
            ),
            embed=None,
            view=catch_view,
        )
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

        await interaction.response.edit_message(
            content=(
                f"🎣 **{chosen_name}（{size:.2f}cm）** を釣り上げた！{record_text}\n"
                f"{comment}\n"
                f"📦（所持数: {count}匹 / 最大記録: {inventory[chosen_name]['max_size']:.2f}cm) \n"
                f"🛠️ **釣竿残り耐久:** `{current_rod}/10`{broke_text}\n\n"
                f"👇 **続けて遊ぶ場合はボタンを押してね！**"
            ),
            embed=None,
            view=view,
        )


# --------------------------------------------------
# 🤿 耐久値対応版：磯採りロジック
# --------------------------------------------------
async def do_dive_logic_edit(
    interaction: discord.Interaction, view: discord.ui.View
):
    user_id = str(interaction.user.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": interaction.user.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "seafood": {},
            "dishes": {},
            "durability": {"fishing_rod": 10, "hoe": 10, "spear": 10},
        }

    user = users_data[user_id]
    if "durability" not in user:
        user["durability"] = {"fishing_rod": 10, "hoe": 10, "spear": 10}
    if "spear" not in user["durability"]:
        user["durability"]["spear"] = 10  # ヤスの初期耐久

    # 🤿 ヤスの耐久値チェック
    spear_durability = user["durability"].get("spear", 0)
    if spear_durability <= 0:
        await interaction.response.edit_message(
            content=(
                "💥 **ヤス（突き刺し具）が壊れています！**\n"
                "ショップで新しいヤスを修理・購入してね！\n\n"
                "👇 **メニューに戻る**"
            ),
            embed=None,
            view=view,
        )
        return

    # 耐久値を 1 減らす
    user["durability"]["spear"] -= 1
    current_spear = user["durability"]["spear"]

    # 海の幸の抽選
    all_seafood = load_seafood()
    if not all_seafood:
        await interaction.response.send_message(
            "⚠️ 海の幸データ（seafood.json）が見つかりません！", ephemeral=True
        )
        return

    chosen_item = random.choice(list(all_seafood.keys()))
    item_info = all_seafood[chosen_item]

    if "seafood" not in user:
        user["seafood"] = {}

    user["seafood"][chosen_item] = user["seafood"].get(chosen_item, 0) + 1
    save_user_data(users_data)

    broke_text = "\n⚠️ **ヤスが壊れてしまった！**" if current_spear == 0 else ""

    await interaction.response.edit_message(
        content=(
            f"🤿 **{chosen_item}** をゲットした！\n"
            f"💬 {item_info.get('description', '')}\n"
            f"📦（所持数: {user['seafood'][chosen_item]}個）\n"
            f"🛠️ **ヤス残り耐久:** `{current_spear}/10`{broke_text}\n\n"
            f"👇 **続けて遊ぶ場合はボタンを押してね！**"
        ),
        embed=None,
        view=view,
    )


# --------------------------------------------------
# 🥗 耐久値対応版：野菜収穫ロジック
# --------------------------------------------------
async def do_farm_logic_edit(
    interaction: discord.Interaction, view: discord.ui.View
):
    user_id = str(interaction.user.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": interaction.user.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "dishes": {},
            "durability": {"fishing_rod": 10, "hoe": 10},
        }

    user = users_data[user_id]
    if "durability" not in user:
        user["durability"] = {"fishing_rod": 10, "hoe": 10}

    # 🪓 クワの耐久値チェック
    hoe_durability = user["durability"].get("hoe", 0)
    if hoe_durability <= 0:
        await interaction.response.edit_message(
            content=(
                "💥 **農具（クワ）が壊れています！**\n"
                "新しいクワを用意してね！\n\n"
                "👇 **メニューに戻る**"
            ),
            embed=None,
            view=view,
        )
        return

    # 耐久値を 1 減らす
    user["durability"]["hoe"] -= 1
    current_hoe = user["durability"]["hoe"]

    # 野菜の抽選
    json_path = os.path.join(base_dir, "jsonall", "crops.json")
    with open(json_path, "r", encoding="utf-8") as f:
        all_veggies = json.load(f)

    chosen_veggie = random.choice(list(all_veggies.keys()))
    veggie_info = all_veggies[chosen_veggie]

    if "veggies" not in user:
        user["veggies"] = {}

    user["veggies"][chosen_veggie] = user["veggies"].get(chosen_veggie, 0) + 1
    save_user_data(users_data)

    broke_text = "\n⚠️ **クワが壊れてしまった！**" if current_hoe == 0 else ""

    await interaction.response.edit_message(
        content=(
            f"🥗 **{chosen_veggie}** を収穫した！\n"
            f"💬 {veggie_info.get('description', '')}\n"
            f"📦（所持数: {user['veggies'][chosen_veggie]}個）\n"
            f"🛠️ **クワ残り耐久:** `{current_hoe}/10`{broke_text}\n\n"
            f"👇 **続けて遊ぶ場合はボタンを押してね！**"
        ),
        embed=None,
        view=view,
    )

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
# --------------------------------------------------
# 📦 統一版インベントリ View
# --------------------------------------------------
class InventoryView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

    @discord.ui.button(
        label="🔄 最新表示に更新",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def refresh_inventory(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のインベントリは操作できません！", ephemeral=True
            )
            return

        # 最新データをロードして表示更新
        users_data = load_user_data()
        self.user_data = users_data.get(str(self.author.id), {})

        msg = build_inventory_text(self.author, self.user_data)
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(
        label="📢 VCにお披露目", style=discord.ButtonStyle.success, row=0
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

    @discord.ui.button(
        label="❌ 閉じる", style=discord.ButtonStyle.secondary, row=0
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()


# 📄 インベントリのテキストを組み立てる共通関数
def build_inventory_text(author, user_data):
    msg = f"📦 **{author.display_name} さんの所持アイテム一覧** 📦\n"
    msg += "───────────────────\n"

    inventory = user_data.get("inventory", {})  # 魚
    veggies = user_data.get("veggies", {})  # 野菜
    meats = user_data.get("meats", {})  # お肉
    seafood = user_data.get("seafood", {})  # 海の幸
    seasonings = user_data.get("seasonings", {})  # 調味料
    dishes = user_data.get("dishes", {})  # 料理

    has_any_item = False

    # 1. 🐟 魚
    fishes_text = []
    for fish_name, data in inventory.items():
        count = len(data.get("sizes", []))
        if count > 0:
            max_size = data.get("max_size", 0)
            fishes_text.append(f"・**{fish_name}**: {count}匹 (最大: {max_size}cm)")
    if fishes_text:
        msg += "🐟 **魚**\n" + "\n".join(fishes_text) + "\n\n"
        has_any_item = True

    # 2. 🤿 海の幸
    seafood_text = [
        f"・**{k}**: {v}個" for k, v in seafood.items() if v > 0
    ]
    if seafood_text:
        msg += "🤿 **海の幸**\n" + "\n".join(seafood_text) + "\n\n"
        has_any_item = True

    # 3. 🥗 野菜
    veggies_text = [
        f"・**{k}**: {v}個" for k, v in veggies.items() if v > 0
    ]
    if veggies_text:
        msg += "🥗 **野菜・穀物**\n" + "\n".join(veggies_text) + "\n\n"
        has_any_item = True

    # 4. 🥩 お肉
    meats_text = [f"・**{k}**: {v}個" for k, v in meats.items() if v > 0]
    if meats_text:
        msg += "🥩 **お肉**\n" + "\n".join(meats_text) + "\n\n"
        has_any_item = True

    # 5. 🧂 調味料
    seasonings_text = [
        f"・**{k}**: {v}個" for k, v in seasonings.items() if v > 0
    ]
    if seasonings_text:
        msg += "🧂 **調味料**\n" + "\n".join(seasonings_text) + "\n\n"
        has_any_item = True

    # 6. 🍳 料理
    dishes_text = [f"・**{k}**: {v}個" for k, v in dishes.items() if v > 0]
    if dishes_text:
        msg += "🍳 **作成済み料理**\n" + "\n".join(dishes_text) + "\n\n"
        has_any_item = True

    if not has_any_item:
        msg += "何もアイテムを持っていません！\n`/start` から釣りや農作業、素潜りに行ってみましょう！\n\n"

    msg += "───────────────────"
    return msg

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

class CookingView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data
        self.selected_appliance = "ミキサー"  # 初期値を設定しておく
        self.selected_fishes = []  # 選ばれた素材リスト（初期値は空）

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
                discord.SelectOption(
                    label="オーブン",
                    description="ふっくら・こんがりと焼き上げる",
                    emoji="🔥",
                ),
                discord.SelectOption(
                    label="蒸し器",
                    description="蒸気で旨味を閉じ込めてふっくら蒸しあげる",
                    emoji="💨",
                ),
                discord.SelectOption(
                    label="網焼きグリル",
                    description="直火で香ばしく焼き目をつける",
                    emoji="🍖",
                ),
                discord.SelectOption(
                    label="炊飯器",
                    description="お米と素材の旨味をぎゅっと炊き込む",
                    emoji="🍚",
                ),
                discord.SelectOption(
                    label="土鍋",
                    description="香ばしいおこげと出汁をじっくり染み込ませる",
                    emoji="🍲",
                ),
            ],
        )
        appliance_select.callback = self.on_appliance_select
        self.add_item(appliance_select)

        # 素材・料理の混合選択肢を作成
        ingredient_options = []

        # ① 魚を追加
        for name, data in user_inventory.items():
            count = len(data.get("sizes", []))
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🐟 {name} ({count}匹所持)", value=name
                    )
                )

        # ② 野菜を追加
        user_veggies = user_data.get("veggies", {})
        for name, count in user_veggies.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🥗 {name} ({count}個所持)", value=name
                    )
                )

        # お肉を追加 🥩
        user_meats = user_data.get("meats", {})
        for name, count in user_meats.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🥩 {name} ({count}個所持)", value=name
                    )
                )

        # ③ 調味料を追加
        user_seasonings = user_data.get("seasonings", {})
        for name, count in user_seasonings.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🧂 {name} (所持: {count}個)",
                        value=name,
                        description="市場で購入した調味料",
                    )
                )

        # ④ 料理（中間素材）を追加
        for name, count in user_dishes.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🍳 {name} ({count}個所持)", value=name
                    )
                )

        # ⑤ 海の幸を追加 🤿
        user_seafood = user_data.get("seafood", {})
        for name, count in user_seafood.items():
            if count > 0:
                ingredient_options.append(
                    discord.SelectOption(
                        label=f"🤿 {name} ({count}個所持)", value=name
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
        await interaction.response.defer()

    async def on_fish_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return
        self.selected_fishes = interaction.data["values"]
        await interaction.response.defer()

    @discord.ui.button(
        label="🔥 調理スタート！", style=discord.ButtonStyle.success, row=2
    )
    async def start_cooking(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not self.selected_fishes:
            await interaction.response.send_message(
                "❌ 材料が選択されていません！", ephemeral=True
            )
            return

        # 2. 最新のユーザーデータを取得
        users_data = load_user_data()
        user_id = str(self.author.id)
        user = users_data.get(user_id, {})

        inventory = user.get("inventory", {})
        veggies = user.get("veggies", {})
        dishes = user.get("dishes", {})
        seasonings = user.get("seasonings", {})

# 在庫チェック
        meats = user.get("meats", {})
        seafood = user.get("seafood", {})  # 👈 🌟 追加！
        for item_name in self.selected_fishes:
            in_fish = item_name in inventory
            in_veggie = item_name in veggies
            in_seasoning = item_name in seasonings
            in_meat = item_name in meats
            in_seafood = item_name in seafood  # 👈 🌟 追加！
            in_dish = item_name in dishes

            if not (
                in_fish
                or in_veggie
                or in_seasoning
                or in_meat
                or in_seafood  # 👈 🌟 条件に追加！
                or in_dish
            ):
                await interaction.response.send_message(
                    f"❌ {item_name} の在庫がありません！",
                    ephemeral=True,
                )
                return

        # 消費処理
        for item in self.selected_fishes:
            fish_sizes = inventory.get(item, {}).get("sizes", [])

            if len(fish_sizes) > 0:
                fish_sizes.pop(0)
            elif veggies.get(item, 0) > 0:
                veggies[item] -= 1
                if veggies[item] <= 0:
                    del veggies[item]
            elif seasonings.get(item, 0) > 0:
                seasonings[item] -= 1
                if seasonings[item] <= 0:
                    del seasonings[item]
            elif meats.get(item, 0) > 0:
                meats[item] -= 1
                if meats[item] <= 0:
                    del meats[item]
            elif seafood.get(item, 0) > 0:  # 👈 🌟 海の幸の消費処理を追加！
                seafood[item] -= 1
                if seafood[item] <= 0:
                    del seafood[item]
            elif dishes.get(item, 0) > 0:
                dishes[item] -= 1
                if dishes[item] <= 0:
                    del dishes[item]

        save_user_data(users_data)

        # 5. レシピ判定＆画面呼び出し
        sorted_fishes = sorted(self.selected_fishes)
        recipe_key = f"{self.selected_appliance}_" + "_".join(sorted_fishes)
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
                f"🍳 **{', '.join(self.selected_fishes)}** で調理開始！\n"
                "💡 この組み合わせのレシピがすでに存在します！\n"
                "既存の料理を作るか、新しく料理名を考案するか選んでください！",
                view=select_view,
                ephemeral=True,
            )
        else:
            modal = NameDishModal(
                recipe_key=recipe_key,
                appliance=self.selected_appliance,
                selected_fishes=self.selected_fishes,
                user=self.author,
            )
            await interaction.response.send_modal(modal)



# 🐟 40cm以下の小魚用 View（メインメニュー上書き対応版）
class CatchOrReleaseView(discord.ui.View):

    def __init__(
        self, author, fish_name, size, comment, is_new_record, users_data
    ):
        super().__init__(timeout=60)
        self.author = author
        self.fish_name = fish_name
        self.size = size
        self.comment = comment
        self.is_new_record = is_new_record
        self.users_data = users_data

    # ① キープするボタン
    @discord.ui.button(
        label="📦 キープする", style=discord.ButtonStyle.success
    )
    async def btn_keep(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        user_id = str(self.author.id)
        inventory = self.users_data[user_id]["inventory"]

        if self.fish_name not in inventory:
            inventory[self.fish_name] = {"sizes": [], "max_size": 0}

        inventory[self.fish_name]["sizes"].append(self.size)
        if self.is_new_record:
            inventory[self.fish_name]["max_size"] = self.size

        save_user_data(self.users_data)
        count = len(inventory[self.fish_name]["sizes"])

        main_view = MainMenuView(author=self.author)
        await interaction.response.edit_message(
            content=(
                f"📦 **{self.fish_name}（{self.size}cm）** を持ち帰りました！\n"
                f"（所持数: {count}匹 / 最大記録: {inventory[self.fish_name]['max_size']}cm）\n\n"
                f"👇 **続けて遊ぶ場合はボタンを押してね！**"
            ),
            view=main_view,
        )

    # ② リリリースするボタン
    @discord.ui.button(
        label="🌊 リリリースする", style=discord.ButtonStyle.secondary
    )
    async def btn_release(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            return

        main_view = MainMenuView(author=self.author)
        await interaction.response.edit_message(
            content=(
                f"🌊 **{self.fish_name}（{self.size}cm）** を海に逃がしました。\n"
                f"（また大きくなって帰ってきてね！）\n\n"
                f"👇 **続けて遊ぶ場合はボタンを押してね！**"
            ),
            view=main_view,
        )
# --------------------------------------------------
# 🧂 調味料購入用 View
# --------------------------------------------------
class BuySeasoningView(discord.ui.View):

    # 商品リスト（名前: [価格, 説明, エモジ]）
    SEASONINGS = {
        "醤油": [20, "刺身や焼き魚、煮物には欠かせない万能調味料！", "🍾"],
        "塩": [10, "素材の旨味を引き立てる基本の調味料。", "🧂"],
        "砂糖": [15, "甘くておいしい砂糖。煮物のコク出しにも！", "🍬"],
        "マヨネーズ": [30, "何にかけても美味しくなる魔法の調味料！", "🧴"],
        "唐辛子": [25, "ピリッと辛いアクセント。辛党向け！", "🌶️"],
    }

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

        options = []
        for name, info in self.SEASONINGS.items():
            price, desc, emoji = info
            options.append(
                discord.SelectOption(
                    label=f"{name} ({price} NP)",
                    description=desc,
                    value=name,
                    emoji=emoji,
                )
            )

        select = discord.ui.Select(
            placeholder="購入したい調味料を選んでください", options=options
        )
        select.callback = self.on_select_buy
        self.add_item(select)

    async def on_select_buy(self, interaction: discord.Interaction):
        item_name = interaction.data["values"][0]
        price = self.SEASONINGS[item_name][0]

        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        coins = user.get("coins", 0)

        if coins < price:
            await interaction.response.send_message(
                f"❌ **NPが足りません！**（{item_name}は {price} NP必要です）",
                ephemeral=True,
            )
            return

        # 代金を引く
        user["coins"] -= price

        # seasonings 辞書の初期化＆加算
        if "seasonings" not in user:
            user["seasonings"] = {}
        user["seasonings"][item_name] = user["seasonings"].get(item_name, 0) + 1

        save_user_data(users_data)

        await interaction.response.send_message(
            f"✨ **{item_name}** を1個購入しました！\n"
            f"📦 所持数: **{user['seasonings'][item_name]}個** / 💰 残高: **{user['coins']} NP**",
            ephemeral=True,
        )

    # ② 🎯 選択して個別売却（ドロップダウンを開く）
    @discord.ui.button(
        label="🎯 選択して個別売却",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def open_select_sell(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})

        # 個別売却用ドロップダウンViewを表示
        sell_select_view = IndividualSellView(
            author=self.author, user_data=user
        )
        if not sell_select_view.has_items:
            await interaction.response.send_message(
                "📦 売却できる素材がありません！", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🏧 **売却したい素材（1個ずつ/1匹ずつ）を選択してください：**",
            view=sell_select_view,
            ephemeral=True,
        )

    # ③ ❌ 閉じるボタン
    @discord.ui.button(
        label="❌ 閉じる", style=discord.ButtonStyle.secondary, row=2
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()


# --------------------------------------------------
# 🥩 精肉店（お肉購入用） View
# --------------------------------------------------
class BuyMeatView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

        meats = load_meats()
        options = []
        for name, info in meats.items():
            price = info.get("price", 100)
            desc = info.get("description", "")
            emoji = info.get("emoji", "🥩")
            options.append(
                discord.SelectOption(
                    label=f"{name} ({price} NP)",
                    description=desc,
                    value=name,
                    emoji=emoji,
                )
            )

        if options:
            select = discord.ui.Select(
                placeholder="購入したいお肉を選んでください",
                options=options,
            )
            select.callback = self.on_select_buy
            self.add_item(select)

    async def on_select_buy(self, interaction: discord.Interaction):
        item_name = interaction.data["values"][0]
        meats = load_meats()
        price = meats.get(item_name, {}).get("price", 100)

        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        coins = user.get("coins", 0)

        if coins < price:
            await interaction.response.send_message(
                f"❌ **NPが足りません！**（{item_name}は {price} NP必要です）",
                ephemeral=True,
            )
            return

        user["coins"] -= price

        if "meats" not in user:
            user["meats"] = {}
        user["meats"][item_name] = user["meats"].get(item_name, 0) + 1

        save_user_data(users_data)

        await interaction.response.send_message(
            f"✨ **{item_name}** を1個購入しました！\n"
            f"📦 所持数: **{user['meats'][item_name]}個** / 💰 残高: **{user['coins']} NP**",
            ephemeral=True,
        )


# --------------------------------------------------
# 🎯 個別売却用 Dropdown View
# --------------------------------------------------
class IndividualSellView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.has_items = False

        inventory = user_data.get("inventory", {})
        veggies = user_data.get("veggies", {})
        dishes = user_data.get("dishes", {})

        options = []

        # 魚の選択肢（先頭1匹のサイズを表示）
        for name, info in inventory.items():
            sizes = info.get("sizes", [])
            if len(sizes) > 0:
                options.append(
                    discord.SelectOption(
                        label=f"🐟 {name} (1匹売却 / {sizes[0]}cm)",
                        value=f"fish_{name}",
                    )
                )

        # 野菜の選択肢
        for name, count in veggies.items():
            if count > 0:
                options.append(
                    discord.SelectOption(
                        label=f"🥗 {name} (1個売却 / 所持: {count}個)",
                        value=f"veg_{name}",
                    )
                )

        # 料理の選択肢（料理も高値で売れる！）
        for name, count in dishes.items():
            if count > 0:
                options.append(
                    discord.SelectOption(
                        label=f"🍳 {name} (1個売却 / 所持: {count}個)",
                        value=f"dish_{name}",
                    )
                )

        if options:
            self.has_items = True
            select = discord.ui.Select(
                placeholder="売却するアイテムを1つ選んでください",
                options=options[:25],  # Discord制限(最大25個)
            )
            select.callback = self.on_select_sell
            self.add_item(select)

    async def on_select_sell(self, interaction: discord.Interaction):
        selected_value = interaction.data["values"][0]

        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})

        earned = 0
        item_name = ""

        # 魚の売却
        if selected_value.startswith("fish_"):
            item_name = selected_value.replace("fish_", "")
            sizes = user.get("inventory", {}).get(item_name, {}).get("sizes", [])
            if sizes:
                s = sizes.pop(0)  # 1匹消費
                earned = 15 + int(s * 0.5)

        # 野菜の売却
        elif selected_value.startswith("veg_"):
            item_name = selected_value.replace("veg_", "")
            if user.get("veggies", {}).get(item_name, 0) > 0:
                user["veggies"][item_name] -= 1
                earned = 10

        # 料理の売却
        elif selected_value.startswith("dish_"):
            item_name = selected_value.replace("dish_", "")
            if user.get("dishes", {}).get(item_name, 0) > 0:
                user["dishes"][item_name] -= 1
                earned = 50  # 料理は高価！

        if earned > 0:
            user["coins"] = user.get("coins", 0) + earned
            save_user_data(users_data)
            await interaction.response.send_message(
                f"💵 **{item_name}** を売却しました！\n"
                f"売却額: **+{earned} NP** (所持金: **{user['coins']} NP**)",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ 在庫がありません！", ephemeral=True
            )

# --------------------------------------------------
# 🛒 市場・ショップ View（レイアウト整列＆閉じる/戻るボタン復活版）
# --------------------------------------------------
class ShopView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=180)
        self.author = author
        self.user_data = user_data

    # --- 1段目 (row=0): 道具の修理 -------------------
    @discord.ui.button(
        label="🎣 釣竿を修理 (100 NP)",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def buy_rod(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        coins = user.get("coins", 0)

        if coins < 100:
            await interaction.response.send_message(
                "❌ **NPが足りません！**（必要: 100 NP）", ephemeral=True
            )
            return

        user["coins"] -= 100
        if "durability" not in user:
            user["durability"] = {}
        user["durability"]["fishing_rod"] = 10

        save_user_data(users_data)
        await interaction.response.send_message(
            f"✨ **釣竿を修理しました！** (耐久: 10/10)\n💰 残高: **{user['coins']} NP**",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🪓 クワを修理 (100 NP)",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def buy_hoe(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        coins = user.get("coins", 0)

        if coins < 100:
            await interaction.response.send_message(
                "❌ **NPが足りません！**（必要: 100 NP）", ephemeral=True
            )
            return

        user["coins"] -= 100
        if "durability" not in user:
            user["durability"] = {}
        user["durability"]["hoe"] = 10

        save_user_data(users_data)
        await interaction.response.send_message(
            f"✨ **クワを修理しました！** (耐久: 10/10)\n💰 残高: **{user['coins']} NP**",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🤿 ヤスを修理 (100 NP)",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def buy_spear(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        coins = user.get("coins", 0)

        if coins < 100:
            await interaction.response.send_message(
                "❌ **NPが足りません！**（必要: 100 NP）", ephemeral=True
            )
            return

        user["coins"] -= 100
        if "durability" not in user:
            user["durability"] = {}
        user["durability"]["spear"] = 10

        save_user_data(users_data)
        await interaction.response.send_message(
            f"✨ **ヤスを修理しました！** (耐久: 10/10)\n💰 残高: **{user['coins']} NP**",
            ephemeral=True,
        )

    # --- 2段目 (row=1): ショップ＆出荷 -----------------
    @discord.ui.button(
        label="🧂 調味料を買う", style=discord.ButtonStyle.primary, row=1
    )
    async def buy_seasoning(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})

        seasoning_view = BuySeasoningView(author=self.author, user_data=user)
        await interaction.response.send_message(
            f"🧂 **調味料専門店**（所持金: **{user.get('coins', 0)} NP**）\n"
            f"料理の隠し味に使える調味料を購入できます！",
            view=seasoning_view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="⚡ 魚・野菜を一括売却",
        style=discord.ButtonStyle.danger,
        row=1,
    )

    async def sell_all(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        inventory = user.get("inventory", {})
        veggies = user.get("veggies", {})

        total_earned = 0
        sold_fishes_count = 0
        sold_veggies_count = 0

        json_path_fish = os.path.join(base_dir, "jsonall", "fishes.json")
        json_path_veg = os.path.join(base_dir, "jsonall", "crops.json")

        all_fishes = {}
        all_veggies = {}
        if os.path.exists(json_path_fish):
            with open(json_path_fish, "r", encoding="utf-8") as f:
                all_fishes = json.load(f)
        if os.path.exists(json_path_veg):
            with open(json_path_veg, "r", encoding="utf-8") as f:
                all_veggies = json.load(f)

        for fish_name, fish_info in list(inventory.items()):
            sizes = fish_info.get("sizes", [])
            base_price = all_fishes.get(fish_name, {}).get("price", 15)
            for s in sizes:
                earned = base_price + int(s * 0.5)
                total_earned += earned
                sold_fishes_count += 1
            fish_info["sizes"] = []

        for veg_name, count in list(veggies.items()):
            if count > 0:
                base_price = all_veggies.get(veg_name, {}).get("price", 10)
                total_earned += base_price * count
                sold_veggies_count += count
                veggies[veg_name] = 0

        if total_earned == 0:
            await interaction.response.send_message(
                "📦 売却できる魚や野菜を持っていません！", ephemeral=True
            )
            return

        user["coins"] = user.get("coins", 0) + total_earned
        save_user_data(users_data)

        # 画面の所持金表示も即座に更新！
        await interaction.response.edit_message(
            content=(
                f"🏧 **にゃっこクラフト中央市場**\n"
                f"💰 あなたの所持金: **{user['coins']} NP**\n\n"
                f"✨ **一括出荷が完了しました！（+{total_earned} NP）**\n"
                f"🐟 魚: {sold_fishes_count}匹 / 🥗 野菜: {sold_veggies_count}個"
            ),
            view=self,
        )


    # 🌟 お肉を買うボタン
    @discord.ui.button(
        label="🥩 お肉を買う", style=discord.ButtonStyle.primary, row=1
    )
    async def buy_meat(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})

        meat_view = BuyMeatView(author=self.author, user_data=user)
        await interaction.response.send_message(
            f"🥩 **にゃっこ精肉店**（所持金: **{user.get('coins', 0)} NP**）\n"
            f"料理のメインディッシュに使えるお肉を購入できます！",
            view=meat_view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🎯 選択売却", style=discord.ButtonStyle.success, row=1
    )
    async def open_select_sell(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})

        sell_select_view = IndividualSellView(
            author=self.author, user_data=user
        )
        if not sell_select_view.has_items:
            await interaction.response.send_message(
                "📦 売却できる素材がありません！", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🏧 **売却したい素材を選択してください：**",
            view=sell_select_view,
            ephemeral=True,
        )

    # --- 3段目 (row=2): ナビゲーション -----------------
    @discord.ui.button(
        label="↩️ メニューに戻る", style=discord.ButtonStyle.secondary, row=2
    )
    async def btn_back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        main_view = MainMenuView(author=self.author)
        await interaction.response.edit_message(
            content="🐱 **にゃっこBot メインメニュー**\n下のボタンを押すだけで、全ての機能が遊べます！",
            embed=None,
            view=main_view,
        )

    @discord.ui.button(
        label="❌ 閉じる", style=discord.ButtonStyle.danger, row=2
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.stop()
        await interaction.message.delete()    


# --------------------------------------------------
# 📋 デイリークエスト View
# --------------------------------------------------
class QuestView(discord.ui.View):

    def __init__(self, author, user_data):
        super().__init__(timeout=60)
        self.author = author
        self.user_data = user_data

    @discord.ui.button(
        label="🎁 クエスト品を納品する",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def complete_quest(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "他の人のクエスト画面は操作できません！", ephemeral=True
            )
            return

        users_data = load_user_data()
        user = users_data.get(str(self.author.id), {})
        q_data = get_daily_quest(user)

        if not q_data or q_data.get("locked"):
            await interaction.response.send_message(
                "⚠️ 現在進行可能なクエストがありません！", ephemeral=True
            )
            return

        if q_data.get("completed"):
            await interaction.response.send_message(
                "✅ 本日のデイリークエストは既に達成済みです！また明日挑戦してね！",
                ephemeral=True,
            )
            return

        quest = q_data["quest"]
        target_item = quest["item"]
        req_count = quest.get("count", 1)
        reward = quest.get("reward_coins", 250)

        # 所持料理（dishes）のチェック
        dishes = user.get("dishes", {})
        if dishes.get(target_item, 0) < req_count:
            await interaction.response.send_message(
                f"❌ 納品に必要な **『{target_item}』** を持っていません！\n"
                f"`/cook` で作ってからもう一度納品してね！",
                ephemeral=True,
            )
            return

        # 料理の消費
        dishes[target_item] -= req_count
        if dishes[target_item] <= 0:
            del dishes[target_item]

        # 報酬の付与とステータス更新
        q_data["completed"] = True
        user["coins"] = user.get("coins", 0) + reward
        save_user_data(users_data)

        await interaction.response.edit_message(
            content=(
                f"🎉 **デイリークエスト達成！**\n"
                f"🐱 「『{target_item}』を届けてくれてありがとうにゃ！おいしかったにゃ！」\n\n"
                f"💰 **報酬: +{reward} NP ゲット！**（現在の所持金: **{user['coins']} NP**）\n"
                f"✨ また明日新しいお願いをチェックしてね！"
            ),
            view=DeleteMessageView(author=self.author),
        )

    @discord.ui.button(
        label="❌ 閉じる", style=discord.ButtonStyle.secondary, row=0
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()

# --------------------------------------------------
# 🎮 メインメニュー View（上書き ＆ 閉じるボタン付き）
# --------------------------------------------------
class MainMenuView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=180)  # 3分間操作可能
        self.author = author

    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "これは他の人のメインメニューです！`/start` で自分用を開いてね！",
                ephemeral=True,
            )
            return False
        return True

    # 1段目: アクション
    @discord.ui.button(
        label="🎣 釣りをする", style=discord.ButtonStyle.primary, row=0
    )
    async def btn_fish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # 画面をそのまま上書き更新して釣りを実行！
        await do_fish_logic_edit(interaction, self)

    @discord.ui.button(
        label="🍎 陸の恵み（収穫）", style=discord.ButtonStyle.success, row=0
    )
    async def btn_farm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await do_farm_logic_edit(interaction, self)

    @discord.ui.button(
        label="📦 インベントリ", style=discord.ButtonStyle.secondary, row=0
    )
    async def btn_bag(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user_id = str(self.author.id)
        users_data = load_user_data()
        user_data = users_data.get(user_id, {})

        view = InventoryView(author=self.author, user_data=user_data)
        await interaction.response.send_message(
            f"📦 **{self.author.display_name} さんのインベントリ**",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="🤿 磯採りに行く", style=discord.ButtonStyle.primary, row=0
    )
    async def btn_dive(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await do_dive_logic_edit(interaction, self)

    # 2段目: 経済・クラフト系
    @discord.ui.button(
        label="🍳 料理をする", style=discord.ButtonStyle.primary, row=1
    )
    async def btn_cook(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # 🌟 ここで最新のユーザーデータをJSONから読み直す！
        users_data = load_user_data()
        user_data = users_data.get(str(self.author.id), {})

        # 最新の user_data を渡して View を作成
        view = CookingView(author=self.author, user_data=user_data)

        # メインメニューを料理画面に上書き編集（または send_message）
        await interaction.response.edit_message(
            content="🍳 **調理器具と使う材料を選んでください！**",
            embed=None,
            view=view,
        )

    @discord.ui.button(
        label="💰 市場・ショップ", style=discord.ButtonStyle.success, row=1
    )
    async def btn_sell(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user_data = users_data.get(str(self.author.id), {})

        # 上書き用の ShopView を作成
        view = ShopView(author=self.author, user_data=user_data)
        coins = user_data.get("coins", 0)

        # 🌟 edit_message でメインメニュー画面自体を「市場」に書き換える！
        await interaction.response.edit_message(
            content=(
                f"🏧 **にゃっこクラフト中央市場**\n"
                f"💰 あなたの所持金: **{coins} NP**\n\n"
                f"道具の修理や、手に入れた素材の出荷ができます！"
            ),
            embed=None,  # メインメニューのEmbedを消去
            view=view,
        )

    @discord.ui.button(
        label="📖 料理図鑑", style=discord.ButtonStyle.secondary, row=1
    )
    async def btn_recipes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        recipes = load_recipes()
        embed = discord.Embed(
            title="📖 発見済み料理レシピ図鑑", color=discord.Color.gold()
        )

        has_recipe = False
        for appliance, dish_list in recipes.items():
            if dish_list:
                has_recipe = True
                text = ""
                for dish in dish_list:
                    ingredients = ", ".join(dish.get("ingredients", []))
                    text += f"・**{dish['name']}** (考案: {dish.get('author', '不明')})\n   └ 材料: {ingredients}\n"
                embed.add_field(
                    name=f"🍳 {appliance}", value=text, inline=False
                )

        if not has_recipe:
            embed.description = "まだ誰も料理を発見していません！"

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="📋 本日のリクエスト",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def btn_quest(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        users_data = load_user_data()
        user_data = users_data.get(str(self.author.id), {})
        q_data = get_daily_quest(user_data)
        save_user_data(users_data)

        # 🔒 ロック中の表示分岐
        if q_data.get("locked"):
            msg = (
                f"🔒 **デイリークエストはまだ解放されていません！**\n"
                f"───────────────────\n"
                f"🍳 みんなで発見したレシピ: **{q_data['count']} / {q_data['needed']} 種類**\n"
                f"💬 「料理のレシピが **10種類** を超えると、にゃっこから日替わりのお願いが届くようになるにゃ！」\n"
                f"👉 `/cook` で色々な食材や器具を試して、新しいレシピを発見しよう！\n"
                f"───────────────────"
            )
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # 🔓 通常表示
        quest = q_data["quest"]
        status_text = (
            "✅ **【達成済み】**"
            if q_data["completed"]
            else "⏳ **【挑戦中】**"
        )

        msg = (
            f"📅 **本日の限定リクエスト**（{q_data['date']}）\n"
            f"ステータス: {status_text}\n"
            f"───────────────────\n"
            f"💬 **にゃっこからの願い**: {quest['description']}\n"
            f"🎯 **目標**: **{quest['item']}** × `{quest['count']}個` を納品\n"
            f"💰 **報酬**: **{quest['reward_coins']} NP**\n"
            f"───────────────────"
        )
        view = QuestView(author=self.author, user_data=user_data)
        await interaction.response.send_message(
            msg, view=view, ephemeral=True
        )
        
    # 🌟 3段目: 閉じるボタン（メッセージ削除）
    @discord.ui.button(
        label="❌ メニューを閉じる",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.stop()
        # このパネル（メッセージ）自体を削除してログを綺麗にする！
        await interaction.message.delete()


class DeleteMessageView(discord.ui.View):

    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(
        label="❌ 閉じる", style=discord.ButtonStyle.secondary
    )
    async def btn_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # ボタンが押されたらメッセージ自体を削除！
        await interaction.message.delete()


# --------------------------------------------------
# 🤖 BOTコマンド群
# --------------------------------------------------


# 1. インベントリ確認コマンド
@bot.hybrid_command(
    name="bag",
    aliases=["inv", "バッグ"],
    description="インベントリを表示します（VCお披露目も可能）",
)
async def inventory(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()
    user_data = users_data.get(user_id, {})

    msg = build_inventory_text(ctx.author, user_data)
    view = InventoryView(author=ctx.author, user_data=user_data)
    await ctx.send(msg, view=view)


# 2. 釣りコマンド
@bot.hybrid_command(name="fish", description="魚を釣り上げます")
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
@bot.hybrid_command(
    name="cook", aliases=["料理"], description="料理をクラフト・命名します"
)
async def cook(ctx):
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
@bot.hybrid_command(
    name="recipes",
    aliases=["レシピ"],
    description="発見された全料理のレシピ図鑑を表示します",
)
async def show_recipes(ctx):
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
            f"💸 **{chosen_fish}（{fish_size:.2f}cm）** を売却しました！\n"
            f"💰 **+{unit_price} NP** 獲得！（現在の所持金: **{user['coins']} NP**）"
        )


# --------------------------------------------------
# 💰 売却コマンド
# --------------------------------------------------
@bot.hybrid_command(
    name="sell", aliases=["売却"], description="魚を市場に売却してNPを獲得します"
)
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


# --------------------------------------------------
# 🥗 野菜収穫コマンド
# --------------------------------------------------
@bot.hybrid_command(
    name="farm",
    aliases=["収穫", "野菜"],
    description="野菜を収穫します",
)
async def harvest_veggies(ctx):
    json_path = os.path.join(base_dir, "jsonall", "crops.json")

    if not os.path.exists(json_path):
        await ctx.send(
            "⚠️ `jsonall/crops.json` が見つかりません！ファイルを作成してください！"
        )
        return

    with open(json_path, "r", encoding="utf-8") as f:
        all_veggies = json.load(f)

    veggie_names = list(all_veggies.keys())
    chosen_veggie = random.choice(veggie_names)
    veggie_info = all_veggies[chosen_veggie]

    user_id = str(ctx.author.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": ctx.author.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "dishes": {},
        }

    user = users_data[user_id]
    if "veggies" not in user:
        user["veggies"] = {}

    veggies = user["veggies"]
    veggies[chosen_veggie] = veggies.get(chosen_veggie, 0) + 1

    save_user_data(users_data)

    await ctx.send(
        f"🥗 **{chosen_veggie}** を収穫した！\n"
        f"💬 {veggie_info.get('description', '')}\n"
        f"📦（所持数: {veggies[chosen_veggie]}個）"
    )

@bot.hybrid_command(
    name="dive",
    aliases=["磯採り", "素潜り"],
    description="素潜りで海の幸（貝やタコ）を採取します",
)
async def dive_command(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()

    if user_id not in users_data:
        users_data[user_id] = {
            "name": ctx.author.name,
            "coins": 100,
            "inventory": {},
            "veggies": {},
            "seafood": {},
            "dishes": {},
            "durability": {"fishing_rod": 10, "hoe": 10, "spear": 10},
        }

    user = users_data[user_id]
    if "durability" not in user:
        user["durability"] = {"fishing_rod": 10, "hoe": 10, "spear": 10}
    if "spear" not in user["durability"]:
        user["durability"]["spear"] = 10

    # 🛠️ 耐久値チェック
    spear_durability = user["durability"].get("spear", 0)
    if spear_durability <= 0:
        await ctx.send(
            "💥 **ヤス（突き刺し具）が壊れています！**\n"
            "ショップ（`/start` や `/sell`）で新しいヤスを修理してね！"
        )
        return

    # 耐久値を 1 減らす
    user["durability"]["spear"] -= 1
    current_spear = user["durability"]["spear"]

    all_seafood = load_seafood()
    if not all_seafood:
        await ctx.send(
            "⚠️ `jsonall/seafood.json` が見つかりません！ファイルを作成してください！"
        )
        return

    chosen_item = random.choice(list(all_seafood.keys()))
    item_info = all_seafood[chosen_item]

    if "seafood" not in user:
        user["seafood"] = {}

    user["seafood"][chosen_item] = user["seafood"].get(chosen_item, 0) + 1
    save_user_data(users_data)

    broke_text = "\n⚠️ **ヤスが壊れてしまった！**" if current_spear == 0 else ""

    await ctx.send(
        f"🤿 **{chosen_item}** をゲットした！\n"
        f"💬 {item_info.get('description', '')}\n"
        f"📦（所持数: {user['seafood'][chosen_item]}個）\n"
        f"🛠️ **ヤス残り耐久:** `{current_spear}/10`{broke_text}"
    )

# --------------------------------------------------
# 📖 にゃっこヘルプコマンド
# --------------------------------------------------
@bot.hybrid_command(
    name="nyakko_help",
    aliases=["nyakko", "にゃっこヘルプ"],
    description="にゃっこBotのコマンド一覧と使い方を表示します",
)
async def nyakko_help(ctx):
    embed = discord.Embed(
        title="🐱 にゃっこBot コマンド一覧",
        description="`/`（スラッシュ）を入力すると選択肢から簡単に実行できます！",
        color=discord.Color.teal(),
    )

    embed.add_field(
        name="🎣 採取・アクティビティ",
        value=(
            "`/fish` : 魚を釣る（40cm以下はリリース選択可）\n"
            "`/farm` : 野菜やお米を収穫する\n"
            "`/dive` : 素潜りで海の幸（タコ・貝類など）を採取する"
        ),
        inline=False,
    )
    embed.add_field(
        name="🍳 調理・レシピ",
        value=(
            "`/cook` : 器具と素材を選んで料理をクラフト！\n"
            "`/recipes` : みんなが発見した料理図鑑を見る"
        ),
        inline=False,
    )
    embed.add_field(
        name="📦 アイテム・マーケット",
        value=(
            "`/bag` : 全所持アイテムの確認（VCお披露目もここから！）\n"
            "`/sell` : 魚や野菜を売って NP（コイン）を獲得・市場を開く"
        ),
        inline=False,
    )
    embed.add_field(
        name="🚀 メイン操作パネル",
        value="`/start` : 全機能がボタン一つで遊べるメインメニューを開く",
        inline=False,
    )

    embed.set_footer(text="💡 スラッシュコマンド（/）に対応！道具の耐久値に注意して遊んでね！")

    # 🌟 閉じるボタン（DeleteMessageView）を添えて送信！
    view = DeleteMessageView(author=ctx.author)
    await ctx.send(embed=embed, view=view)

# --------------------------------------------------
# 🚀 メインメニューコマンド（/start）
# --------------------------------------------------
@bot.hybrid_command(
    name="start",
    aliases=["スタート", "menu"],
    description="にゃっこBotのメインパネルを開きます（全機能がボタンで操作可能）",
)
async def start_menu(ctx):
    embed = discord.Embed(
        title="🐱 にゃっこBot メインメニュー",
        description="下のボタンを押すだけで、全ての機能が遊べます！",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="🎮 遊べる機能",
        value=(
            "🎣 **釣りをする** : 魚を吊り上げます\n"
            "🥗 **野菜収穫** : 料理に使う野菜をゲット\n"
            "📦 **インベントリ** : 手持ち確認・VCお披露目\n"
            "🍳 **料理をする** : クラフト＆新レシピ考案\n"
            "💰 **魚を売る** : NPを獲得\n"
            "📖 **料理図鑑** : レシピ一覧をチェック"
        ),
        inline=False,
    )
    embed.set_footer(text="💡 ボタンを押してゲームを開始しよう！")

    view = MainMenuView(author=ctx.author)
    await ctx.send(embed=embed, view=view)


@bot.hybrid_command(
    name="quest",
    aliases=["クエスト", "デイリー"],
    description="本日のデイリーリクエストを確認・納品します",
)
async def quest_command(ctx):
    user_id = str(ctx.author.id)
    users_data = load_user_data()
    user_data = users_data.get(user_id, {})

    q_data = get_daily_quest(user_data)
    save_user_data(users_data)

    if not q_data:
        await ctx.send("⚠️ クエストデータが読み込めませんでした！")
        return

    # 🔒 2. レシピが10種類未満（ロック中）の表示処理！
    if q_data.get("locked"):
        msg = (
            f"🔒 **デイリークエストはまだ解放されていません！**\n"
            f"───────────────────\n"
            f"🍳 みんなで発見したレシピ: **{q_data['count']} / {q_data['needed']} 種類**\n"
            f"💬 「料理のレシピが **10種類** を超えると、にゃっこから日替わりのお願いが届くようになるにゃ！」\n"
            f"👉 `/cook` で色々な食材や器具を試して、新しいレシピを発見しよう！\n"
            f"───────────────────"
        )
        view = DeleteMessageView(author=ctx.author)
        await ctx.send(msg, view=view)
        return

    # 🔓 10種類以上ある場合の通常表示
    quest = q_data["quest"]
    status_text = (
        "✅ **【達成済み】**" if q_data["completed"] else "⏳ **【挑戦中】**"
    )

    msg = (
        f"📅 **本日の限定リクエスト**（{q_data['date']}）\n"
        f"ステータス: {status_text}\n"
        f"───────────────────\n"
        f"💬 **にゃっこからの願い**: {quest['description']}\n"
        f"🎯 **目標**: **{quest['item']}** × `{quest['count']}個` を納品\n"
        f"💰 **報酬**: **{quest['reward_coins']} NP**\n"
        f"───────────────────"
    )

    view = QuestView(author=ctx.author, user_data=user_data)
    await ctx.send(msg, view=view)

bot.run(TOKEN)