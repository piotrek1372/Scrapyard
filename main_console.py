from src.core.scrapyard import Scrapyard
from src.utils.i18n import I18n, t, t_item

def main():
    i18n = I18n()
    print(f"[i18n] Language: {i18n.get_language()}")

    yard = Scrapyard()
    print(t("game.overlooking"))

    for _ in range(5):
        founded_item = yard.loot()
        print(t("loot.found", name=t_item(founded_item.name), model=founded_item.model_path))


if __name__ == "__main__":
    main()