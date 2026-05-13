import json
import os

langs = {
    "de": {
        "menu": {"welcome": "Willkommen zurück, {nick}!", "balance": "Guthaben: ${balance}", "play": "Spielen", "load_game": "Spiel laden", "profile": "Profil", "settings": "Einstellungen", "quit": "Beenden"},
        "pause": {"title": "PAUSIERT", "resume": "Fortsetzen", "save_game": "Spiel speichern", "settings": "Einstellungen", "main_menu": "Hauptmenü"},
        "settings": {"title": "Einstellungen", "tab_graphics": "Grafik", "tab_audio": "Audio", "tab_performance": "Leistung", "tab_language": "Sprache", "save": "Speichern", "cancel": "Abbrechen", "resolution": "Auflösung", "fullscreen": "Vollbild", "vsync": "VSync", "msaa": "Kantenglättung", "render_distance": "Sichtweite", "master_volume": "Gesamtlautstärke", "music_volume": "Musik", "sfx_volume": "Effekte", "muted": "Stumm", "shadow_quality": "Schattenqualität", "texture_quality": "Texturqualität", "fps_limit": "FPS-Limit", "fps_unlimited": "Unbegrenzt", "saved": "Einstellungen gespeichert."},
        "profile": {"title": "Profil", "nick_label": "Spitzname", "balance_label": "Guthaben", "created_label": "Mitglied seit", "playtime_label": "Gesamtspielzeit", "save": "Änderungen speichern", "saved": "Profil gespeichert.", "back": "Zurück"},
        "saves": {"title_load": "Spiel laden", "title_save": "Spiel speichern", "load": "Laden", "save": "Speichern", "delete": "Löschen", "confirm_delete": "Diesen Spielstand löschen?", "yes": "Ja", "no": "Nein", "save_name_placeholder": "Name des Spielstands...", "no_saves": "Keine Spielstände gefunden.", "saving": "Speichern...", "saved": "Gespeichert!"},
        "new_profile": {"title": "Wie heißt du, Schrottsammler?", "placeholder": "Spitznamen eingeben...", "start": "Abenteuer beginnen", "error_short": "Der Name muss mindestens 3 Zeichen lang sein.", "error_long": "Der Name darf höchstens 20 Zeichen lang sein."}
    },
    "fr": {
        "menu": {"welcome": "Bon retour, {nick}!", "balance": "Solde : ${balance}", "play": "Jouer", "load_game": "Charger la partie", "profile": "Profil", "settings": "Paramètres", "quit": "Quitter"},
        "pause": {"title": "PAUSE", "resume": "Reprendre", "save_game": "Sauvegarder", "settings": "Paramètres", "main_menu": "Menu principal"},
        "settings": {"title": "Paramètres", "tab_graphics": "Graphismes", "tab_audio": "Audio", "tab_performance": "Performances", "tab_language": "Langue", "save": "Enregistrer", "cancel": "Annuler", "resolution": "Résolution", "fullscreen": "Plein écran", "vsync": "VSync", "msaa": "Anticrénelage", "render_distance": "Distance d'affichage", "master_volume": "Volume principal", "music_volume": "Musique", "sfx_volume": "Effets sonores", "muted": "Muet", "shadow_quality": "Qualité des ombres", "texture_quality": "Qualité des textures", "fps_limit": "Limite de FPS", "fps_unlimited": "Illimité", "saved": "Paramètres enregistrés."},
        "profile": {"title": "Profil", "nick_label": "Pseudo", "balance_label": "Solde", "created_label": "Membre depuis", "playtime_label": "Temps de jeu total", "save": "Enregistrer", "saved": "Profil enregistré.", "back": "Retour"},
        "saves": {"title_load": "Charger la partie", "title_save": "Sauvegarder la partie", "load": "Charger", "save": "Sauvegarder", "delete": "Supprimer", "confirm_delete": "Supprimer cette sauvegarde ?", "yes": "Oui", "no": "Non", "save_name_placeholder": "Nom de la sauvegarde...", "no_saves": "Aucune sauvegarde trouvée.", "saving": "Sauvegarde en cours...", "saved": "Sauvegardé !"},
        "new_profile": {"title": "Comment tu t'appelles, ferrailleur ?", "placeholder": "Entrez votre pseudo...", "start": "Commencer l'aventure", "error_short": "Le nom doit comporter au moins 3 caractères.", "error_long": "Le nom doit comporter au maximum 20 caractères."}
    },
    "es": {
        "menu": {"welcome": "¡Bienvenido de nuevo, {nick}!", "balance": "Saldo: ${balance}", "play": "Jugar", "load_game": "Cargar partida", "profile": "Perfil", "settings": "Ajustes", "quit": "Salir"},
        "pause": {"title": "PAUSA", "resume": "Reanudar", "save_game": "Guardar partida", "settings": "Ajustes", "main_menu": "Menú principal"},
        "settings": {"title": "Ajustes", "tab_graphics": "Gráficos", "tab_audio": "Audio", "tab_performance": "Rendimiento", "tab_language": "Idioma", "save": "Guardar", "cancel": "Cancelar", "resolution": "Resolución", "fullscreen": "Pantalla completa", "vsync": "VSync", "msaa": "Suavizado", "render_distance": "Distancia de dibujado", "master_volume": "Volumen maestro", "music_volume": "Música", "sfx_volume": "Efectos", "muted": "Silenciado", "shadow_quality": "Calidad de sombras", "texture_quality": "Calidad de texturas", "fps_limit": "Límite de FPS", "fps_unlimited": "Ilimitado", "saved": "Ajustes guardados."},
        "profile": {"title": "Perfil", "nick_label": "Apodo", "balance_label": "Saldo", "created_label": "Miembro desde", "playtime_label": "Tiempo total jugado", "save": "Guardar cambios", "saved": "Perfil guardado.", "back": "Volver"},
        "saves": {"title_load": "Cargar partida", "title_save": "Guardar partida", "load": "Cargar", "save": "Guardar", "delete": "Eliminar", "confirm_delete": "¿Eliminar esta partida?", "yes": "Sí", "no": "No", "save_name_placeholder": "Nombre de la partida...", "no_saves": "No se encontraron partidas.", "saving": "Guardando...", "saved": "¡Guardado!"},
        "new_profile": {"title": "¿Cómo te llamas, chatarrero?", "placeholder": "Introduce tu apodo...", "start": "Comenzar aventura", "error_short": "El nombre debe tener al menos 3 caracteres.", "error_long": "El nombre debe tener como máximo 20 caracteres."}
    },
    "it": {
        "menu": {"welcome": "Bentornato, {nick}!", "balance": "Saldo: ${balance}", "play": "Gioca", "load_game": "Carica partita", "profile": "Profilo", "settings": "Impostazioni", "quit": "Esci"},
        "pause": {"title": "PAUSA", "resume": "Riprendi", "save_game": "Salva partita", "settings": "Impostazioni", "main_menu": "Menu principale"},
        "settings": {"title": "Impostazioni", "tab_graphics": "Grafica", "tab_audio": "Audio", "tab_performance": "Prestazioni", "tab_language": "Lingua", "save": "Salva", "cancel": "Annulla", "resolution": "Risoluzione", "fullscreen": "Schermo intero", "vsync": "VSync", "msaa": "Anti-Aliasing", "render_distance": "Distanza di rendering", "master_volume": "Volume principale", "music_volume": "Musica", "sfx_volume": "Effetti sonori", "muted": "Muto", "shadow_quality": "Qualità ombre", "texture_quality": "Qualità texture", "fps_limit": "Limite FPS", "fps_unlimited": "Illimitato", "saved": "Impostazioni salvate."},
        "profile": {"title": "Profilo", "nick_label": "Soprannome", "balance_label": "Saldo", "created_label": "Membro dal", "playtime_label": "Tempo di gioco totale", "save": "Salva modifiche", "saved": "Profilo salvato.", "back": "Indietro"},
        "saves": {"title_load": "Carica partita", "title_save": "Salva partita", "load": "Carica", "save": "Salva", "delete": "Elimina", "confirm_delete": "Eliminare questo salvataggio?", "yes": "Sì", "no": "No", "save_name_placeholder": "Nome salvataggio...", "no_saves": "Nessun salvataggio trovato.", "saving": "Salvataggio...", "saved": "Salvato!"},
        "new_profile": {"title": "Come ti chiami, rottamatore?", "placeholder": "Inserisci il soprannome...", "start": "Inizia l'avventura", "error_short": "Il nome deve contenere almeno 3 caratteri.", "error_long": "Il nome deve contenere al massimo 20 caratteri."}
    },
    "pt": {
        "menu": {"welcome": "Bem-vindo de volta, {nick}!", "balance": "Saldo: ${balance}", "play": "Jogar", "load_game": "Carregar Jogo", "profile": "Perfil", "settings": "Configurações", "quit": "Sair"},
        "pause": {"title": "PAUSADO", "resume": "Retomar", "save_game": "Salvar Jogo", "settings": "Configurações", "main_menu": "Menu Principal"},
        "settings": {"title": "Configurações", "tab_graphics": "Gráficos", "tab_audio": "Áudio", "tab_performance": "Desempenho", "tab_language": "Idioma", "save": "Salvar", "cancel": "Cancelar", "resolution": "Resolução", "fullscreen": "Tela Cheia", "vsync": "VSync", "msaa": "Anti-Aliasing", "render_distance": "Distância de Renderização", "master_volume": "Volume Principal", "music_volume": "Música", "sfx_volume": "Efeitos Sonoros", "muted": "Mudo", "shadow_quality": "Qualidade das Sombras", "texture_quality": "Qualidade das Texturas", "fps_limit": "Limite de FPS", "fps_unlimited": "Ilimitado", "saved": "Configurações salvas."},
        "profile": {"title": "Perfil", "nick_label": "Apelido", "balance_label": "Saldo", "created_label": "Membro desde", "playtime_label": "Tempo total de jogo", "save": "Salvar Alterações", "saved": "Perfil salvo.", "back": "Voltar"},
        "saves": {"title_load": "Carregar Jogo", "title_save": "Salvar Jogo", "load": "Carregar", "save": "Salvar", "delete": "Excluir", "confirm_delete": "Excluir este jogo salvo?", "yes": "Sim", "no": "Não", "save_name_placeholder": "Nome do jogo salvo...", "no_saves": "Nenhum jogo salvo encontrado.", "saving": "Salvando...", "saved": "Salvo!"},
        "new_profile": {"title": "Como você se chama, sucateiro?", "placeholder": "Digite seu apelido...", "start": "Começar a Aventura", "error_short": "O nome deve ter pelo menos 3 caracteres.", "error_long": "O nome deve ter no máximo 20 caracteres."}
    },
    "ru": {
        "menu": {"welcome": "С возвращением, {nick}!", "balance": "Баланс: ${balance}", "play": "Играть", "load_game": "Загрузить игру", "profile": "Профиль", "settings": "Настройки", "quit": "Выход"},
        "pause": {"title": "ПАУЗА", "resume": "Продолжить", "save_game": "Сохранить игру", "settings": "Настройки", "main_menu": "Главное меню"},
        "settings": {"title": "Настройки", "tab_graphics": "Графика", "tab_audio": "Звук", "tab_performance": "Производ-ность", "tab_language": "Язык", "save": "Сохранить", "cancel": "Отмена", "resolution": "Разрешение", "fullscreen": "На весь экран", "vsync": "Верт. синхронизация", "msaa": "Сглаживание", "render_distance": "Дальность прорисовки", "master_volume": "Общая громкость", "music_volume": "Музыка", "sfx_volume": "Эффекты", "muted": "Без звука", "shadow_quality": "Качество теней", "texture_quality": "Качество текстур", "fps_limit": "Лимит FPS", "fps_unlimited": "Без лимита", "saved": "Настройки сохранены."},
        "profile": {"title": "Профиль", "nick_label": "Никнейм", "balance_label": "Баланс", "created_label": "В игре с", "playtime_label": "Всего наиграно", "save": "Сохранить изменения", "saved": "Профиль сохранен.", "back": "Назад"},
        "saves": {"title_load": "Загрузить игру", "title_save": "Сохранить игру", "load": "Загрузить", "save": "Сохранить", "delete": "Удалить", "confirm_delete": "Удалить это сохранение?", "yes": "Да", "no": "Нет", "save_name_placeholder": "Название сохранения...", "no_saves": "Сохранений не найдено.", "saving": "Сохранение...", "saved": "Сохранено!"},
        "new_profile": {"title": "Как тебя звать, сборщик?", "placeholder": "Введите ник...", "start": "Начать приключение", "error_short": "Имя должно содержать не менее 3 символов.", "error_long": "Имя должно содержать не более 20 символов."}
    },
    "tr": {
        "menu": {"welcome": "Tekrar hoş geldin, {nick}!", "balance": "Bakiye: ${balance}", "play": "Oyna", "load_game": "Oyun Yükle", "profile": "Profil", "settings": "Ayarlar", "quit": "Çıkış"},
        "pause": {"title": "DURAKLATILDI", "resume": "Devam Et", "save_game": "Oyunu Kaydet", "settings": "Ayarlar", "main_menu": "Ana Menü"},
        "settings": {"title": "Ayarlar", "tab_graphics": "Grafikler", "tab_audio": "Ses", "tab_performance": "Performans", "tab_language": "Dil", "save": "Kaydet", "cancel": "İptal", "resolution": "Çözünürlük", "fullscreen": "Tam Ekran", "vsync": "VSync", "msaa": "Kenar Yumuşatma", "render_distance": "Görüş Mesafesi", "master_volume": "Ana Ses", "music_volume": "Müzik", "sfx_volume": "Efektler", "muted": "Sessiz", "shadow_quality": "Gölge Kalitesi", "texture_quality": "Doku Kalitesi", "fps_limit": "FPS Sınırı", "fps_unlimited": "Sınırsız", "saved": "Ayarlar kaydedildi."},
        "profile": {"title": "Profil", "nick_label": "Kullanıcı Adı", "balance_label": "Bakiye", "created_label": "Katılım Tarihi", "playtime_label": "Toplam Oynama", "save": "Değişiklikleri Kaydet", "saved": "Profil kaydedildi.", "back": "Geri"},
        "saves": {"title_load": "Oyun Yükle", "title_save": "Oyunu Kaydet", "load": "Yükle", "save": "Kaydet", "delete": "Sil", "confirm_delete": "Bu kaydı sil?", "yes": "Evet", "no": "Hayır", "save_name_placeholder": "Kayıt adı...", "no_saves": "Kayıt bulunamadı.", "saving": "Kaydediliyor...", "saved": "Kaydedildi!"},
        "new_profile": {"title": "Adın ne hurdacı?", "placeholder": "Kullanıcı adı girin...", "start": "Maceraya Başla", "error_short": "Ad en az 3 karakter olmalıdır.", "error_long": "Ad en fazla 20 karakter olmalıdır."}
    },
    "ar": {
        "menu": {"welcome": "مرحباً بعودتك، {nick}!", "balance": "الرصيد: ${balance}", "play": "العب", "load_game": "تحميل لعبة", "profile": "الملف الشخصي", "settings": "الإعدادات", "quit": "خروج"},
        "pause": {"title": "متوقف مؤقتاً", "resume": "استئناف", "save_game": "حفظ اللعبة", "settings": "الإعدادات", "main_menu": "القائمة الرئيسية"},
        "settings": {"title": "الإعدادات", "tab_graphics": "الرسومات", "tab_audio": "الصوت", "tab_performance": "الأداء", "tab_language": "اللغة", "save": "حفظ", "cancel": "إلغاء", "resolution": "الدقة", "fullscreen": "ملء الشاشة", "vsync": "مزامنة رأسية", "msaa": "تنعيم الحواف", "render_distance": "مسافة العرض", "master_volume": "مستوى الصوت الرئيسي", "music_volume": "الموسيقى", "sfx_volume": "المؤثرات", "muted": "كتم الصوت", "shadow_quality": "جودة الظلال", "texture_quality": "جودة الخامات", "fps_limit": "حد الإطارات", "fps_unlimited": "غير محدود", "saved": "تم حفظ الإعدادات."},
        "profile": {"title": "الملف الشخصي", "nick_label": "الاسم المستعار", "balance_label": "الرصيد", "created_label": "عضو منذ", "playtime_label": "إجمالي وقت اللعب", "save": "حفظ التغييرات", "saved": "تم حفظ الملف.", "back": "رجوع"},
        "saves": {"title_load": "تحميل لعبة", "title_save": "حفظ اللعبة", "load": "تحميل", "save": "حفظ", "delete": "حذف", "confirm_delete": "حذف هذا الحفظ؟", "yes": "نعم", "no": "لا", "save_name_placeholder": "اسم الحفظ...", "no_saves": "لم يتم العثور على ملفات حفظ.", "saving": "جاري الحفظ...", "saved": "تم الحفظ!"},
        "new_profile": {"title": "ما اسمك يا جامع الخردة؟", "placeholder": "أدخل الاسم المستعار...", "start": "ابدأ المغامرة", "error_short": "يجب أن يكون الاسم 3 أحرف على الأقل.", "error_long": "يجب أن يكون الاسم 20 حرفاً كحد أقصى."}
    },
    "zh": {
        "menu": {"welcome": "欢迎回来，{nick}！", "balance": "余额：${balance}", "play": "开始游戏", "load_game": "加载游戏", "profile": "个人资料", "settings": "设置", "quit": "退出"},
        "pause": {"title": "已暂停", "resume": "继续", "save_game": "保存游戏", "settings": "设置", "main_menu": "主菜单"},
        "settings": {"title": "设置", "tab_graphics": "图形", "tab_audio": "音频", "tab_performance": "性能", "tab_language": "语言", "save": "保存", "cancel": "取消", "resolution": "分辨率", "fullscreen": "全屏", "vsync": "垂直同步", "msaa": "抗锯齿", "render_distance": "渲染距离", "master_volume": "主音量", "music_volume": "音乐", "sfx_volume": "音效", "muted": "静音", "shadow_quality": "阴影质量", "texture_quality": "纹理质量", "fps_limit": "FPS 限制", "fps_unlimited": "无限制", "saved": "设置已保存。"},
        "profile": {"title": "个人资料", "nick_label": "昵称", "balance_label": "余额", "created_label": "加入时间", "playtime_label": "总游戏时间", "save": "保存更改", "saved": "个人资料已保存。", "back": "返回"},
        "saves": {"title_load": "加载游戏", "title_save": "保存游戏", "load": "加载", "save": "保存", "delete": "删除", "confirm_delete": "确认删除此存档？", "yes": "是", "no": "否", "save_name_placeholder": "存档名称...", "no_saves": "未找到存档。", "saving": "保存中...", "saved": "已保存！"},
        "new_profile": {"title": "你叫什么名字，拾荒者？", "placeholder": "输入昵称...", "start": "开始冒险", "error_short": "名称必须至少 3 个字符。", "error_long": "名称最多 20 个字符。"}
    },
    "ja": {
        "menu": {"welcome": "お帰りなさい、{nick}！", "balance": "残高: ${balance}", "play": "プレイ", "load_game": "ロード", "profile": "プロフィール", "settings": "設定", "quit": "終了"},
        "pause": {"title": "一時停止", "resume": "再開", "save_game": "セーブ", "settings": "設定", "main_menu": "メインメニュー"},
        "settings": {"title": "設定", "tab_graphics": "グラフィック", "tab_audio": "オーディオ", "tab_performance": "パフォーマンス", "tab_language": "言語", "save": "保存", "cancel": "キャンセル", "resolution": "解像度", "fullscreen": "フルスクリーン", "vsync": "垂直同期", "msaa": "アンチエイリアス", "render_distance": "描画距離", "master_volume": "マスター音量", "music_volume": "音楽", "sfx_volume": "SE", "muted": "ミュート", "shadow_quality": "影の品質", "texture_quality": "テクスチャの品質", "fps_limit": "FPS上限", "fps_unlimited": "無制限", "saved": "設定を保存しました。"},
        "profile": {"title": "プロフィール", "nick_label": "ニックネーム", "balance_label": "残高", "created_label": "参加日", "playtime_label": "総プレイ時間", "save": "変更を保存", "saved": "プロフィールを保存しました。", "back": "戻る"},
        "saves": {"title_load": "ゲームをロード", "title_save": "ゲームをセーブ", "load": "ロード", "save": "セーブ", "delete": "削除", "confirm_delete": "このセーブデータを削除しますか？", "yes": "はい", "no": "いいえ", "save_name_placeholder": "セーブデータ名...", "no_saves": "セーブデータがありません。", "saving": "保存中...", "saved": "保存しました！"},
        "new_profile": {"title": "君の名前は？スクラッパー。", "placeholder": "ニックネームを入力...", "start": "冒険を始める", "error_short": "名前は3文字以上である必要があります。", "error_long": "名前は20文字以内である必要があります。"}
    },
    "ko": {
        "menu": {"welcome": "돌아온 것을 환영합니다, {nick}!", "balance": "잔고: ${balance}", "play": "플레이", "load_game": "게임 불러오기", "profile": "프로필", "settings": "설정", "quit": "종료"},
        "pause": {"title": "일시 정지", "resume": "계속", "save_game": "게임 저장", "settings": "설정", "main_menu": "메인 메뉴"},
        "settings": {"title": "설정", "tab_graphics": "그래픽", "tab_audio": "오디오", "tab_performance": "성능", "tab_language": "언어", "save": "저장", "cancel": "취소", "resolution": "해상도", "fullscreen": "전체 화면", "vsync": "수직 동기화", "msaa": "안티앨리어싱", "render_distance": "렌더링 거리", "master_volume": "마스터 볼륨", "music_volume": "음악", "sfx_volume": "효과음", "muted": "음소거", "shadow_quality": "그림자 품질", "texture_quality": "텍스처 품질", "fps_limit": "FPS 제한", "fps_unlimited": "제한 없음", "saved": "설정이 저장되었습니다."},
        "profile": {"title": "프로필", "nick_label": "닉네임", "balance_label": "잔고", "created_label": "가입일", "playtime_label": "총 플레이 시간", "save": "변경 사항 저장", "saved": "프로필이 저장되었습니다.", "back": "뒤로"},
        "saves": {"title_load": "게임 불러오기", "title_save": "게임 저장", "load": "불러오기", "save": "저장", "delete": "삭제", "confirm_delete": "이 저장 데이터를 삭제하시겠습니까?", "yes": "예", "no": "아니요", "save_name_placeholder": "저장 이름...", "no_saves": "저장 데이터가 없습니다.", "saving": "저장 중...", "saved": "저장되었습니다!"},
        "new_profile": {"title": "이름이 뭡니까, 수집가?", "placeholder": "닉네임 입력...", "start": "모험 시작", "error_short": "이름은 3자 이상이어야 합니다.", "error_long": "이름은 최대 20자까지만 가능합니다."}
    },
    "hi": {
        "menu": {"welcome": "वापसी पर स्वागत है, {nick}!", "balance": "बैलेंस: ${balance}", "play": "खेलें", "load_game": "गेम लोड करें", "profile": "प्रोफ़ाइल", "settings": "सेटिंग्स", "quit": "बाहर निकलें"},
        "pause": {"title": "रोका गया", "resume": "फिर से शुरू करें", "save_game": "गेम सहेजें", "settings": "सेटिंग्स", "main_menu": "मुख्य मेनू"},
        "settings": {"title": "सेटिंग्स", "tab_graphics": "ग्राफ़िक्स", "tab_audio": "ऑडियो", "tab_performance": "प्रदर्शन", "tab_language": "भाषा", "save": "सहेजें", "cancel": "रद्द करें", "resolution": "रिज़ॉल्यूशन", "fullscreen": "पूर्ण स्क्रीन", "vsync": "VSync", "msaa": "एंटी-अलियासिंग", "render_distance": "रेंडर दूरी", "master_volume": "मुख्य आवाज़", "music_volume": "संगीत", "sfx_volume": "प्रभाव", "muted": "म्यूट", "shadow_quality": "छाया की गुणवत्ता", "texture_quality": "बनावट की गुणवत्ता", "fps_limit": "FPS सीमा", "fps_unlimited": "असीमित", "saved": "सेटिंग्स सहेजी गईं।"},
        "profile": {"title": "प्रोफ़ाइल", "nick_label": "उपनाम", "balance_label": "बैलेंस", "created_label": "सदस्यता की शुरुआत", "playtime_label": "कुल खेल का समय", "save": "परिवर्तन सहेजें", "saved": "प्रोफ़ाइल सहेजी गई।", "back": "वापस"},
        "saves": {"title_load": "गेम लोड करें", "title_save": "गेम सहेजें", "load": "लोड करें", "save": "सहेजें", "delete": "हटाएं", "confirm_delete": "क्या यह सेव हटाएं?", "yes": "हां", "no": "नहीं", "save_name_placeholder": "सेव का नाम...", "no_saves": "कोई सेव नहीं मिला।", "saving": "सहेज रहा है...", "saved": "सहेजा गया!"},
        "new_profile": {"title": "तुम्हारा नाम क्या है, कबाड़ी?", "placeholder": "उपनाम दर्ज करें...", "start": "रोमांच शुरू करें", "error_short": "नाम कम से कम 3 वर्णों का होना चाहिए।", "error_long": "नाम अधिकतम 20 वर्णों का हो सकता है।"}
    },
    "bn": {
        "menu": {"welcome": "আবার স্বাগতম, {nick}!", "balance": "ব্যালেন্স: ${balance}", "play": "খেলুন", "load_game": "গেম লোড করুন", "profile": "প্রোফাইল", "settings": "সেটিংস", "quit": "প্রস্থান করুন"},
        "pause": {"title": "পজ করা হয়েছে", "resume": "পুনরায় শুরু করুন", "save_game": "গেম সেভ করুন", "settings": "সেটিংস", "main_menu": "প্রধান মেনু"},
        "settings": {"title": "সেটিংস", "tab_graphics": "গ্রাফিক্স", "tab_audio": "অডিও", "tab_performance": "কর্মক্ষমতা", "tab_language": "ভাষা", "save": "সেভ করুন", "cancel": "বাতিল করুন", "resolution": "রেজোলিউশন", "fullscreen": "ফুলস্ক্রিন", "vsync": "VSync", "msaa": "অ্যান্টি-অ্যালিয়াসিং", "render_distance": "রেন্ডার দূরত্ব", "master_volume": "মাস্টার ভলিউম", "music_volume": "সঙ্গীত", "sfx_volume": "শব্দের প্রভাব", "muted": "মিউট", "shadow_quality": "ছায়ার মান", "texture_quality": "টেক্সচারের মান", "fps_limit": "FPS সীমা", "fps_unlimited": "সীমাহীন", "saved": "সেটিংস সেভ হয়েছে।"},
        "profile": {"title": "প্রোফাইল", "nick_label": "ডাকনাম", "balance_label": "ব্যালেন্স", "created_label": "সদস্য হয়েছেন", "playtime_label": "মোট খেলার সময়", "save": "পরিবর্তন সেভ করুন", "saved": "প্রোফাইল সেভ হয়েছে।", "back": "পিছনে"},
        "saves": {"title_load": "গেম লোড করুন", "title_save": "গেম সেভ করুন", "load": "লোড", "save": "সেভ", "delete": "মুছে ফেলুন", "confirm_delete": "এই সেভ মুছে ফেলবেন?", "yes": "হ্যাঁ", "no": "না", "save_name_placeholder": "সেভের নাম...", "no_saves": "কোনো সেভ পাওয়া যায়নি।", "saving": "সেভ হচ্ছে...", "saved": "সেভ করা হয়েছে!"},
        "new_profile": {"title": "তোমার নাম কী, স্ক্র্যাপার?", "placeholder": "ডাকনাম লিখুন...", "start": "অ্যাডভেঞ্চার শুরু করুন", "error_short": "নাম কমপক্ষে ৩ অক্ষরের হতে হবে।", "error_long": "নাম সর্বোচ্চ ২০ অক্ষরের হতে পারে।"}
    }
}

base_dir = r"c:\Users\piotr\Desktop\Scrapyard\data\lang"

for lang, data in langs.items():
    file_path = os.path.join(base_dir, f"{lang}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
        
        # update sections
        for section, content in data.items():
            if section not in original_data:
                original_data[section] = content
        
        # sort if needed, or just dump
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f, ensure_ascii=False, indent=4)
        print(f"Updated {lang}.json")
