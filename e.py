import pandas as pd
import numpy as np

columns = [
    'Аватарка',
    'Фамилия Имя',
    'Институт',
    'Группа',
    'Ссылка VK',
    'Почта',
    'Подходящие типы проектов',
    'Список компетенций',
    'Выбранные проекты',
    'Ищет команду',
]
print(pd.read_csv('students.csv', encoding='cp1251', index_col=0).iloc[1][6:-1])
