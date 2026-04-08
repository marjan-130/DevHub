from model import DataModel
from view import MainView
from controller import AppController

def main():
    # 1. Ініціалізуємо Модель
    model = DataModel()
    
    # 2. Ініціалізуємо View
    view = MainView()
    
    # 3. Створюємо Контролер
    app = AppController(model, view)
    view.app_logic = app 
    
    # 5. Запуск
    view.start()

if __name__ == "__main__":
    main()