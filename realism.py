import os
import json
import discord

# ==================================================
# 💾 地名マスタ（map_master.json）の読み込み
# ==================================================
def load_map_master():
    """realjsonalld フォルダ内の map_master.json を読み込む"""
    file_path = os.path.join("realjsonalld", "map_master.json")
    
    if not os.path.exists(file_path):
        print(f"⚠️ Warning: {file_path} が見つかりません。")
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# マスタデータの読み込み
MAP_MASTER = load_map_master()

# ==================================================
# 💾 サーバー別 データの読み書き関数
# ==================================================
def get_realism_file_path(guild_id):
    """realjsonalld フォルダ内に保存パスを作成"""
    os.makedirs("realjsonalld", exist_ok=True)
    return os.path.join("realjsonalld", f"realism_data_{guild_id}.json")

def load_realism_data(guild_id):
    file_path = get_realism_file_path(guild_id)
    if not os.path.exists(file_path):
        # 初期マップ設定
        return {
            "selected_region": {},  # ユーザーごとの選択中エリア
            "maps": {}              # 区画データ
        }
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_realism_data(guild_id, data):
    file_path = get_realism_file_path(guild_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================================================
# 🏛️ 都道府県 選択ドロップダウン (Select)
# ==================================================
class PrefectureSelect(discord.ui.Select):
    def __init__(self, region_key, prefectures_data):
        self.region_key = region_key
        self.prefectures_data = prefectures_data

        options = []
        for pref_key, pref_info in prefectures_data.items():
            options.append(
                discord.SelectOption(
                    label=pref_info["name"],
                    value=pref_key,
                    description=f"{pref_info['name']}の市町村開発画面へ",
                    emoji="🏛️"
                )
            )
        super().__init__(placeholder="🏙️ 開発・移動したい都道府県を選択してください...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_pref_key = self.values[0]
        pref_info = self.prefectures_data.get(selected_pref_key, {})
        pref_name = pref_info.get("name", "不明な県")

        # 今後はここから「市・区・町・村選択」または「区画グリッド画面」へ進む
        await interaction.response.send_message(
            f"📍 **【{pref_name}】** が選択されました！\n"
            f"含まれる自治体: {', '.join(pref_info.get('cities', []))}\n\n"
            f"※ ここから市町村を選択して、開発グリッド（🟩 🛣️ 🏢）へ移動します（実装準備中）",
            ephemeral=True
        )


# ==================================================
# 🗺️ 地方詳細 View（詳細マップ画像 ＋ 県選択）
# ==================================================
class RegionDetailView(discord.ui.View):
    def __init__(self, author, user_data, region_key, prefectures_data):
        super().__init__(timeout=180)
        self.author = author
        self.user_data = user_data
        
        # 県選択ドロップダウンを追加
        self.add_item(PrefectureSelect(region_key, prefectures_data))

    @discord.ui.button(label="🔙 地方一覧に戻る", style=discord.ButtonStyle.secondary, row=2)
    async def btn_back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ 他の人の操作はできません！", ephemeral=True)
            return
        
        # トップの全体マップ・地方選択画面へ戻る
        await send_realism_menu(interaction, self.author, self.user_data)


# ==================================================
# 🗺️ 地方選択ドロップダウン (Select)
# ==================================================
class RegionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="北坂道", value="hokusakado", emoji="❄️", description="最北の広大な自然エリア"),
            discord.SelectOption(label="東埼地方", value="tousai", emoji="🌲", description="東部の広大な山脈と沿岸エリア"),
            discord.SelectOption(label="仙東地方", value="sento", emoji="🏙️", description="中央東寄りの都市・インフラ中心地"),
            discord.SelectOption(label="中海地方", value="chukai", emoji="🌊", description="中央部の豊かな内陸・沿岸エリア"),
            discord.SelectOption(label="仙西地方", value="sensai", emoji="🌾", description="西部の商業・農業エリア"),
            discord.SelectOption(label="八州地方", value="hasshu", emoji="🌴", description="南西に広がる開拓・海洋エリア"),
        ]
        super().__init__(placeholder="🗺️ 移動・開発したい地方を選択してください...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        region_key = self.values[0]
        region_info = MAP_MASTER.get(region_key, {})

        if not region_info:
            await interaction.response.send_message("⚠️ 地方データが見つかりませんでした。", ephemeral=True)
            return

        region_name = region_info.get("name", "地方")
        image_name = region_info.get("image", f"{region_key}.png")
        prefectures = region_info.get("prefectures", {})

        # Embedの作成
        embed = discord.Embed(
            title=f"🗾 架空国家『日新国』 - {region_name} 詳細マップ",
            description=(
                f"📍 **現在地**: 🏛️ {region_name} 特区\n\n"
                "下のドロップダウンメニューから、開発したい**都道府県**を選択してください！"
            ),
            color=0x3498db
        )

        # 詳細マップ画像の読み込み・添付
        files = []
        if os.path.exists(image_name):
            file = discord.File(image_name, filename=image_name)
            embed.set_image(url=f"attachment://{image_name}")
            files.append(file)

        # 県選択用のViewへ遷移
        view = RegionDetailView(
            author=interaction.user,
            user_data={},
            region_key=region_key,
            prefectures_data=prefectures
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            attachments=files,
            view=view
        )


# ==================================================
# 🏙️ 現実化モード メイン View
# ==================================================
class RealismMainView(discord.ui.View):
    def __init__(self, author, user_data):
        super().__init__(timeout=180)
        self.author = author
        self.user_data = user_data
        
        # 地方選択ドロップダウンを追加
        self.add_item(RegionSelect())

    # --- 🔙 にゃっこタウンに戻る ---
    @discord.ui.button(label="🔙 にゃっこタウンに戻る", style=discord.ButtonStyle.danger, row=2)
    async def btn_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ 他の人の操作はできません！", ephemeral=True)
            return

        # main.py から読み込み
        from main import MainMenuView, load_user_data
        
        guild_id = str(interaction.guild_id or "dm")
        users_data = load_user_data(guild_id)
        user = users_data.get(str(self.author.id), {})

        await interaction.response.edit_message(
            content=(
                f"📍 **現在地**: 🌆 にゃっこタウン・中央通り\n"
                f"💰 所持金: **{user.get('coins', 0):,} NP**\n\n"
                f"何をしますか？"
            ),
            embed=None,
            attachments=[],
            view=MainMenuView(author=self.author)
        )


# ==================================================
# 🚀 main.py から呼び出す表示関数
# ==================================================
async def send_realism_menu(interaction: discord.Interaction, author, user_data):
    """全体マップ画像付きで現実化モードを表示する"""
    embed = discord.Embed(
        title="🗾 架空国家『日新国』全土・国土開発マップ",
        description=(
            "📍 **現在地**: 🏛️ 日新国・国土開発特区\n"
            f"💰 所持金: **{user_data.get('coins', 0):,} NP**\n\n"
            "下のドロップダウンメニューから、開発・土地購入を行いたい**地方**を選択してください！"
        ),
        color=0x2b2d31
    )
    
    files = []
    if os.path.exists("all_country.png"):
        file = discord.File("all_country.png", filename="all_country.png")
        embed.set_image(url="attachment://all_country.png")
        files.append(file)

    view = RealismMainView(author=author, user_data=user_data)
    
    await interaction.response.edit_message(
        content=None,
        embed=embed,
        attachments=files,
        view=view
    )