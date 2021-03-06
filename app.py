import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from dash_bootstrap_components.themes import LITERA

import pandas as pd
from collections import Counter
import re
import requests
import psycopg2
import os

TOKEN =

font_family = 'Arial'
testing = False


def debug(email):
    print()
    student_data = get_student_data(email)
    for i in range(len(student_data)):
        print(f'{student_data.index[i]}: {student_data[i]}')
    print()


def get_filter_label(value):
    if value == 'ГМУ':
        return 'Государственное и муниципальное управление (ГМУ)'
    elif value == 'ИБ':
        return 'Информационная безопасность (ИБ)'
    elif value == 'СУБД':
        return 'Базы данных (СУБД)'
    else:
        return value


def get_top_types(professions):
    df_filtered = df[df['Требуемые области деятельности'].apply(
        lambda x: professions.issubset(x.split(', ')))]
    type_list = []
    for row in df_filtered['Тип проекта'].apply(lambda x: x.split(', ')).tolist():
        type_list += row
    type_dict = Counter(type_list)
    sum_ = len(type_list)
    for key in type_dict.keys():
        type_dict[key] /= sum_
    top_types = sorted(type_dict.keys(), key=lambda x: type_dict[x], reverse=True)
    index = len(top_types)
    for i in range(1, len(top_types)):
        if type_dict[top_types[i]] / type_dict[top_types[i - 1]] < 0.8:
            index = i
            break
    top_types = ', '.join(top_types[:index])
    return top_types


def get_vk_name(text, row):
    if row == 0:
        return '(Это вы)'
    elif text.split(':')[0] == text.split(':')[1] or len(text.split(':')) == 1 or not text.split(':')[1]:
        return ''
    else:
        vk_name = text.split(':')[1]
        return f'({vk_name})'


def get_top_students(data, student_data):
    top_list = []
    for row in range(len(data)):
        point = 0
        data_row = data.iloc[row]
        if data_row['Группа'] == student_data[3]:
            point += 1
        if data_row['Группа'].split('/')[0] == student_data[3].split('/')[0]:
            point += 1
        if data_row['Институт'] == student_data[2]:
            point += 1

        point += 3 * len(set(data_row['Выбранные проекты'].split(', ')) & set(student_data[8].split(', ')))
        point += len(set(data_row['Области деятельности'].split(', ')) & set(student_data[7].split(', ')))
        point += len(set(data_row['Подходящие типы проектов'].split(', ')) & set(student_data[6].split(', ')))

        top_list.append(int(point))
    return top_list


def build_delete_button():
    children = html.Div(
        [
            dbc.FormGroup(
                [
                    dbc.Label("Почта", html_for='email-del', width=2,
                              style={'fontWeight': 500}),
                    dbc.Row(
                        [
                            dbc.Input(id="email-delete", value="", placeholder='Например: ivanov.ia@edu.spbstu.ru'),
                            dbc.FormText(
                                id='email-delete-text'),
                        ], style={'width': '75%'}
                    )

                ], row=True
            ),
            dbc.Button(
                children=['УДАЛИТЬ'],
                id='email-delete-button',
                # type='button',
                className='btn btn-outline-success',
                style={'margin-top': '0.5rem',
                       'width': '20%',
                       'fontWeight': 500,
                       'position': 'relative',
                       'left': '40%',
                       # 'type':'button',
                       },
                outline=True,
            )
        ]
    )
    return children


def check_student_in_data(email):
    try:
        get_student_data(email)
        bool = True
    except:
        bool = False
    return bool


def get_student_data(email):
    return db.get_pandas().loc[email]


filter_list = [
    'Программирование', 'Инженерное дело', 'PR', 'Дизайн', 'ГМУ', 'Актив', 'Гуманитарные науки', 'Социология',
    'Менеджмент', 'Управление', 'Физика', 'Работа с фото/видео', 'Зарубежное регионоведение', 'ХимБио',
    'Аналитика', 'Спорт', 'СУБД', 'Психология', 'Математика', 'ИБ', '3D Моделирование', 'Любые'
]
institute_dict = {
    '383': 'ГИ',
    '313': 'ИСИ',
    '473': 'ИБСиБ',
    '483': 'ИКиЗИ',
    '353': 'ИКНТ',
    '333': 'ИММиТ',
    '363': 'ИПММ',
    '343': 'ИФНиТ',
    '323': 'ИЭ',
    '373': 'ИПМЭиТ'
}
student_columns = [
    'Аватарка',
    'Фамилия Имя',
    'Институт',
    'Группа',
    'Ссылка VK',
    'Почта',
    'Подходящие типы проектов',
    'Области деятельности',
    'Выбранные проекты',
    'Ищет команду',
]


class Students:
    def __init__(self, db):
        self.db = db
        if testing:
            pass
        else:
            self.conn = psycopg2.connect(self.db, sslmode='require')
        self.create_students()

    def create_students(self):

        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE if not exists students
                    (Аватарка text, 
                    Фамилия_Имя text, 
                    Институт text,
                    Группа text,
                    Ссылка_VK text,
                    Почта text,
                    Подходящие_типы_проектов text,
                    Области_деятельности text,
                    Выбранные_проекты text,
                    Ищет_команду int)"""
        )
        self.conn.commit()

    def insert_students(self, row):
        cur = self.conn.cursor()
        cur.execute(
            f"""INSERT INTO students VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, NULL, %s)""", row)
        self.conn.commit()

    def update_students(self, row, email, mode):
        cur = self.conn.cursor()
        if mode == 'Анкета':
            row.pop(5)
            row.append(email)
            cur.execute("""UPDATE students
                        SET Аватарка = %s,
                        Фамилия_Имя = %s,
                        Институт = %s,
                        Группа = %s,
                        Ссылка_VK = %s,
                        Ищет_команду = %s
                        WHERE Почта = %s
                        """, tuple(row))
        elif mode == 'Тест':
            cur.execute("""UPDATE students
                        SET Подходящие_типы_проектов = %s,
                        Области_деятельности = %s,
                        Выбранные_проекты = %s
                        WHERE Почта = %s
                        """, tuple(row + [email]))
        self.conn.commit()

    def get_students(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT * FROM students""")
        return cur.fetchall()

    def delete_student(self, emails):
        cur = self.conn.cursor()
        cur.execute(f"""DELETE FROM students WHERE Почта in ({('%s, ' * len(emails))[:-2]})""", tuple(emails))
        self.conn.commit()

    def get_pandas(self):
        data_ = pd.DataFrame(data=self.get_students(), columns=student_columns)
        data_.index = data_['Почта']
        return data_

    def __del__(self):
        self.conn.close()


df = pd.read_excel('opd.xlsx')
if testing:
    DATABASE_URL = ''
else:
    DATABASE_URL = os.environ['DATABASE_URL']

db = Students(DATABASE_URL)

app = dash.Dash(__name__,
                external_stylesheets=[LITERA],
                title="Тест по ОПД",
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1.0, maximum-scale=1.0"},
                ],
                )

name = dbc.FormGroup(
    [
        dbc.Label("Имя", html_for='name-input', width=2,
                  style={'fontWeight': 500}),
        dbc.Row(
            [
                dbc.Input(id="name-input", value="", placeholder='Например: Иван'),
                dbc.FormFeedback(
                    "Корректный ввод", valid=True
                ),
                dbc.FormFeedback(
                    "Некорректный ввод",
                    valid=False,
                ),
            ], style={'width': '75%'}
        )

    ], row=True
)

surname = dbc.FormGroup(
    [
        dbc.Label("Фамилия", html_for='surname-input', width=2,
                  style={'fontWeight': 500}),
        dbc.Row(
            [
                dbc.Input(id="surname-input", value="", placeholder='Например: Иванов'),
                dbc.FormFeedback(
                    "Корректный ввод", valid=True
                ),
                dbc.FormFeedback(
                    "Некорректный ввод",
                    valid=False,
                ),
            ], style={'width': '75%'}
        )

    ], row=True
)
group = dbc.FormGroup(
    [
        dbc.Label("Группа", html_for='group-input', width=2,
                  style={'fontWeight': 500}),
        dbc.Row(
            [
                dbc.Input(id="group-input", value="", placeholder='Например: 3532704/90002',
                          ),
                dbc.FormFeedback(
                    "Корректный ввод", valid=True
                ),
                dbc.FormFeedback(
                    "Некорректный ввод",
                    valid=False,
                ),
            ], style={'width': '75%'}
        )

    ], row=True
)

email = dbc.FormGroup(
    [
        dbc.Label("Почта", html_for='email-input', width=2,
                  style={'fontWeight': 500}),
        dbc.Row(
            [
                dbc.Input(id="email-input", value="", placeholder='Например: ivanov.ia@edu.spbstu.ru'),
                dbc.FormText("Принимаются данные только вашей корпоративной почты"),
                dbc.FormFeedback(
                    "Корректный ввод", valid=True
                ),
                dbc.FormFeedback(
                    "Некорректный ввод",
                    valid=False,
                ),
            ], style={'width': '75%'}
        )

    ], row=True
)

vk_url = dbc.FormGroup(
    [
        dbc.Label("VK", html_for='vk-input', width=2,
                  style={'fontWeight': 500}),
        dbc.Row(
            [
                dbc.InputGroup(
                    [
                        dbc.InputGroupAddon("vk.com/", addon_type="prepend"),
                        dbc.Input(id="vk-input", value="",
                                  placeholder='Например: id139214004 или steeba', ),
                        dbc.FormText("Вводите только ту часть ссылки, которая находится после vk.com/"),
                        dbc.FormFeedback(
                            "Корректный ввод", valid=True
                        ),
                        dbc.FormFeedback(
                            "Некорректный ввод",
                            valid=False,
                        ),
                    ]
                ),

            ], style={'width': '75%'}
        )

    ], row=True
)
need_team = dbc.FormGroup(
    [
        dbc.Checkbox(
            id="need_team_checkbox", className="form-check-input", checked=True
        ),
        dbc.Label(
            "Ищу команду ",
            html_for="need_team_checkbox",
            className="form-check-label",
            style={'fontWeight': 'Bold', 'color': 'SteelBlue'}
        ),
    ],
    check=True,
),
anketa = dbc.Container(
    [
        html.A(id='anketa'),
        html.H3('Анкета',
                style={
                    'text-align': 'center',
                    'fontWeight': 'bold',
                    'padding-bottom': '1rem',
                    'padding-top': '1rem'
                }
                ),
        dbc.Card(
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(name, width=6),
                            dbc.Col(group, width=6)
                        ], style={'height': '6rem'}
                    ),
                    dbc.Row(
                        [
                            dbc.Col(surname, width=6),
                            dbc.Col(email, width=6),
                        ], style={'height': '6rem'}
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(need_team, style={'text-align': 'right', 'margin-right': '4rem'}), width=6),
                            dbc.Col(vk_url, width=6)
                        ], style={'height': '6rem'}
                    ),
                    html.Div(id='description', style={'height': '50%', 'width': '100%'})
                ]
            ), style={'height': '37rem', 'border-radius': 15}
        ),
        html.Div(
            html.A(
                [
                    dbc.Button(
                        children=['ПОДТВЕРДИТЬ'],
                        id='button_anketa',
                        # type='button',
                        className='btn btn-outline-success',
                        style={'margin-top': '0.5rem',
                               'width': '20%',
                               'fontWeight': 500,
                               'position': 'relative',
                               'left': '40%',
                               # 'type':'button',
                               },
                        disabled=True,
                        outline=True,
                    )
                ],
                href='#anketa', id='anchor_button_anketa'),
        ),
    ], fluid=True)

id_input = dbc.FormGroup(
    [
        dbc.Label("Введите ID понравившихся проектов", html_for='id-input', style={'fontWeight': 500}),
        dbc.Label(
            id='id-label', html_for='id-input', style={
                'color': 'SteelBlue',
                'fontWeight': 600,
                'font-size': 14,
                'margin-left': '0.5rem'
            }
        ),
        dbc.Input(id="id-input", value="", placeholder="Например: \"228 322 69\""),
        dbc.FormText("Вводите числа без кавычек через пробел"),
        dbc.FormFeedback(
            "Корректный ввод", valid=True
        ),
        dbc.FormFeedback(
            "Некорректный ввод", id='invalid-input',
            valid=False,
        ),
    ]
)

test = dbc.Container(
    [
        html.H3(
            'Тест по ОПД',
            style={
                'text-align': 'center',
                'fontWeight': 'bold',
                'margin-top': '5rem',
                'padding-bottom': '1rem',
                'padding-top': '1rem'
            }
        ),
        html.A(id='test'),
        dbc.Card(
            dbc.CardBody(
                [
                    dbc.Row(
                        dbc.Col(
                            html.H6(
                                'Выберите интересующие вас области деятельности',
                                style={'color': 'SteelBlue', 'fontWeight': 'bold', 'margin-bottom': '1rem'}
                            ),
                        )
                    ),
                    dbc.Row(
                        [
                            dbc.Col([

                                dcc.Checklist(
                                    id='checkboxes',
                                    options=[
                                        {'label': f' {get_filter_label(filter)}', 'value': filter} for filter in
                                        filter_list
                                    ],
                                    value=[],
                                    labelStyle={
                                        'display': 'block',
                                        'font-size': 13,
                                        'text-align': 'left',
                                        'fontWeight': 500,
                                        'line-height': 12
                                    }

                                )], width=2),
                            dbc.Col(
                                [
                                    html.Div(id='test_table',
                                             style={
                                                 'width': '100%',
                                                 'height': '75%',
                                                 'overflow': 'auto',
                                                 'margin-bottom': '.5rem',
                                                 # 'border': '3px solid green',
                                             }
                                             ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.H4(id='top_types_title',
                                                            style={'fontWeight': 'bold',
                                                                   'text-align': 'left'}),
                                                    html.H6(id='top_types',
                                                            style={'color': 'SteelBlue',
                                                                   'text-align': 'left'})
                                                ], width={'size': 4}, style={'top': '0.5rem'}
                                            ),
                                            dbc.Col(
                                                [
                                                    id_input,

                                                ], style={}
                                            ),
                                        ], style={'width': '98%', 'height': '20%'}
                                    )

                                ], style={'height': '100%'}
                            )
                        ], style={'height': '100%'}
                    )
                ]
            ), style={'height': '42rem', 'border-radius': 15}
        ),
        html.Div(
            html.A(
                dbc.Button(
                    children=['ДАЛЕЕ'],
                    id='button_test',
                    # type='button',
                    disabled=True,
                    className='btn btn-outline-success',
                    outline=True,
                    style={'margin-top': '0.5rem',
                           'width': '20%',
                           'fontWeight': 500,
                           'position': 'relative',
                           'left': '40%',
                           }
                ), href='#search', id='anchor_button_test'
            ), style={'width': '100%'}
        )
    ], fluid=True)

search = dbc.Container(
    [
        html.A(id='search'),
        html.H3('Поиск команды',
                style={
                    'text-align': 'center',
                    'fontWeight': 'bold',
                    'padding-bottom': '1rem',
                    'padding-top': '1rem',
                    'margin-top': '5rem'
                }
                ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        id='search_table',
                        style={
                            'height': '90%',
                            'width': '100%',
                            'overflow': 'auto',
                            'margin-bottom': '.5rem',
                        }
                    ),
                    dbc.Button(
                        children=['ОБНОВИТЬ'],
                        id='button_search',
                        # type='button',
                        className='btn btn-outline-success',
                        style={'margin-top': '0.5rem',
                               'width': '10%',
                               'fontWeight': 500,
                               'position': 'relative',
                               'left': '45%',
                               # 'type':'button',
                               },
                        disabled=True,
                        outline=True,
                    )
                ]
            ), style={'height': '37rem', 'border-radius': 15}
        ),
    ], fluid=True, style={'padding-bottom': '2rem'})

app.layout = html.Div(
    [
        anketa,
        test,
        search
    ], style={
        'font-family': font_family,
        'width': '100%',
        'min-width': 1400,
        'background-color': '#edeef0',
    }

)


@app.callback(

    [
        Output("name-input", 'valid'),
        Output("name-input", 'invalid'),
    ],
    [Input('name-input', 'value')]
)
def get_name_input_is_correct(input):
    if input:
        if re.fullmatch('^([А-Я]{1}[а-яё]{1,23})$', input):
            return True, False
        else:
            return False, True
    else:
        return False, False


@app.callback(

    [
        Output("surname-input", 'valid'),
        Output("surname-input", 'invalid'),
    ],
    [Input('surname-input', 'value')]
)
def get_surname_input_is_correct(input):
    if input:
        if re.fullmatch('^([А-Я]{1}[а-яё]{1,40})$', input):
            return True, False
        else:
            return False, True
    else:
        return False, False


@app.callback(
    [
        Output("group-input", 'valid'),
        Output("group-input", 'invalid'),
    ],
    [Input('group-input', 'value')]
)
def get_group_input_is_correct(input):
    if input:
        if re.fullmatch('^([0-9]{7}/[0-9]{1}000[1-9]{1})$', input) and input[:3] in institute_dict.keys():
            return True, False
        else:
            return False, True
    else:
        return False, False


@app.callback(

    [
        Output("email-input", 'valid'),
        Output("email-input", 'invalid'),
    ],
    [
        Input('email-input', 'value')
    ]
)
def get_email_input_is_correct(input):
    if input:
        if input[1:].endswith('@edu.spbstu.ru'):
            return True, False
        else:
            return False, True
    else:
        return False, False


@app.callback(

    Output("email-delete-text", 'children'),
    [
        Input('email-delete', 'value'),
        Input('email-delete-button', 'n_clicks')
    ]
)
def email_delete(input, button):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if input:
        if 'email-delete-button' in changed_id:
            emails = input.split()
            prev = len(db.get_students())
            db.delete_student(emails)
            now = len(db.get_students())
            if prev != now:
                return f'Успешно удалена(ы) {prev - now} строка(и)'
            else:
                return 'Данные не изменились'
    return 'Введите почту человека для того, чтобы удалить его из базы данных. Можно вести сразу несколько почт через пробел'


@app.callback(

    Output("description", 'children'),
    [
        Input('name-input', 'value'),
        Input('surname-input', 'value'),
    ]
)
def get_description(name, surname):
    if name == 'delete' and surname == 'data':
        return build_delete_button()
    else:
        children = [
            html.Div(
                html.H5('Инструкция'), style={'text-align': 'center', 'width': '100%'}
            ),
            html.Ul(
                [
                    html.Li(
                        """Для начала необходимо заполнить анкету"""
                    ),
                    html.Li(
                        """После заполнения анкеты нажмите на кнопку “ПОДТВЕРДИТЬ”, затем “ДАЛЕЕ”"""
                    ),
                    html.Li(
                        """Выберите подходящие для вас области деятельности"""
                    ),
                    html.Li(
                        """Укажите понравившиеся ID для подбора потенциальных тиммейтов через запятую в поле ниже (не более 5 проектов)"""
                    ),
                    html.Li(
                        """После вам нужно нажать на кнопку “ПОДТВЕРДИТЬ”, затем “ДАЛЕЕ”, вас перекинет в раздел “Поиск команды”"""
                    ),
                    html.Li(
                        """В разделе "Поиск команды" все, что нужно делать - это обновлять таблицу по мере прохождения студентами этого теста нажатием на кнопку “ОБНОВИТЬ”, далее
    выбрать понравившихся кандидатов из списка и написать им, используя их ссылки в VK или почту
    """
                    )
                ], className='list4b'
            )
        ]
        return children


@app.callback(
    Output('button_anketa', 'disabled'),
    [
        Input('group-input', 'valid'),
        Input('name-input', 'valid'),
        Input('surname-input', 'valid'),
        Input('email-input', 'valid'),
    ]
)
def get_button_anketa_enabled(valid1, valid2, valid3, valid4):
    if valid1 and valid2 and valid3 and valid4:
        return False
    else:
        return True


@app.callback(

    [
        Output('vk-input', 'valid'),
        Output('vk-input', 'invalid'),
        Output('anchor_button_anketa', 'href'),
        Output('button_anketa', 'children'),
    ],
    [
        Input('button_anketa', 'n_clicks'),
        Input('vk-input', 'value'),
        Input('group-input', 'value'),
        Input('name-input', 'value'),
        Input('surname-input', 'value'),
        Input('email-input', 'value'),
        Input('need_team_checkbox', 'checked')
    ]
)
def submit_input_anketa(button, vk, group, name, surname, email, need_team):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'button_anketa' in changed_id:
        input_vk = vk
        if re.fullmatch('^(id[0-9]+)$', vk):
            input_vk = input_vk[2:]
        api_url = f'https://api.vk.com/method/users.get?user_ids={input_vk}&access_token={TOKEN}&fields=photo_50&v=5.126'
        r = requests.get(api_url)
        response_dict = r.json()
        if response_dict.get('response'):
            img_url = response_dict['response'][0]['photo_50']
            vk_first_name = response_dict['response'][0]['first_name']
            vk_last_name = response_dict['response'][0]['last_name']
            vk_name = f'{vk_last_name} {vk_first_name}'

            student_data = [
                img_url,
                f'{surname} {name}:{vk_name}',
                institute_dict[group[:3]],
                group,
                f'vk.com/{vk}',
                email,
                1 if need_team else 0
            ]
            if check_student_in_data(email):
                db.update_students(student_data, email, 'Анкета')
            else:
                db.insert_students(student_data)
            return True, False, '#test', 'ДАЛЕЕ'
        else:
            return False, True, '#anketa', 'ПОДТВЕРДИТЬ'
    else:
        return False, False, '#anketa', 'ПОДТВЕРДИТЬ'


@app.callback(

    [
        Output("id-input", 'valid'),
        Output("id-input", 'invalid'),
        Output('invalid-input', 'children')
    ],
    [Input('id-input', 'value')]
)
def get_id_input_is_correct(input):
    invalid_input = 'Некорректный ввод'
    if input:
        try:
            int(input.replace(' ', ''))
            if len(input.split()) > 5:
                invalid_input = 'Вы выбрали слишком много проектов'
                return False, True, invalid_input
            else:
                list_ = list(map(int, input.split()))
                if len(list_) != len(set(list_)):
                    invalid_input = 'Есть совпадающие проекты'
                    return False, True, invalid_input
                elif max(list_) <= len(df) and min(list_) > 0:
                    return True, False, invalid_input
                else:
                    invalid_input = 'Один или несколько проектов не указаны в таблице'
                    return False, True, invalid_input
        except:
            invalid_input = 'Вы используете недопустимые символы'
            return False, True, invalid_input
    else:
        return False, False, invalid_input


@app.callback(
    Output('button_test', 'disabled'),
    [
        Input('id-input', 'valid'),
        Input('id-input', 'invalid'),
        Input("checkboxes", 'value'),
        Input("button_anketa", 'children')
    ]
)
def get_button_test_enabled(valid, invalid, checkboxes, button):
    checkboxes = set(checkboxes)
    length = len(df[df['Требуемые области деятельности'].apply(
        lambda x: checkboxes.issubset(x.split(', ')))])

    if valid and not invalid and checkboxes and length and button == 'ДАЛЕЕ':
        return False
    else:
        return True


@app.callback(
    [
        # Output("id-label", 'children'),
        Output('anchor_button_test', 'href'),
        Output('button_test', 'children'),
    ],
    [
        Input('button_test', 'n_clicks'),
        Input('id-input', 'value'),
        Input('email-input', 'value'),
        Input("checkboxes", 'value'),
    ]
)
def submit_input_test(button, input, email, checkboxes):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'button_test' in changed_id:
        professions = ', '.join(checkboxes)
        checkboxes = set(checkboxes)
        project_types = get_top_types(checkboxes)
        id_labels = ', '.join(input.split())

        student_data = [
            professions,
            project_types,
            id_labels
        ]
        db.update_students(student_data, email, mode='Тест')
        return '#search', 'ДАЛЕЕ'
    else:
        return '#test', 'ПОДТВЕРДИТЬ'


@app.callback(
    Output("test_table", 'children'),
    [
        Input("checkboxes", 'value'),
    ]
)
def get_test_table(checkboxes):
    checkboxes = set(checkboxes)
    columns = ['ID', 'Тип проекта', 'Название проекта', 'Краткое описание', 'Требуемые области деятельности']

    if checkboxes:
        df_test = df[df['Требуемые области деятельности'].apply(
            lambda x: checkboxes.issubset(x.split(', ')))][columns]
    else:
        df_test = df[columns]
    width_iter = [5, 10, 20, 50, 15]
    if not df_test.empty:
        children = dbc.Table(
            [
                html.Table(className='table',
                           style={'width': '100%', 'height': '100%', 'table-layout': 'fixed'}, children=
                           [
                               html.Thead(
                                   html.Tr(
                                       [
                                           html.Th(html.Label(column), style={'width': f'{width_iter[col]}%', }) for
                                           col, column in
                                           enumerate(columns)
                                       ], style={'fontWeight': 'bold', 'text-align': 'center', 'height': '3rem'}
                                   )
                               ),
                               html.Tbody(
                                   [
                                       html.Tr(
                                           [
                                               html.Td(
                                                   f'{df_test.iloc[row, col]}',
                                                   style={
                                                       'width': f'{width_iter[col]}%',
                                                       'font-size': 16 if not col else 12,
                                                       'text-align': 'center' if not col else 'left'
                                                   }
                                               )
                                               for col, column in enumerate(columns)
                                           ]
                                       ) for row in range(len(df_test))
                                   ]
                               )
                           ]
                           )
            ], responsive=True, bordered=True
        )
    else:
        children = html.Div(
            html.H6(
                'Нет подходящих проектов, укажите другой перечень областей деятельности'
            ), style={
                'text-align': 'center',
                'display': 'flex',
                'align-items': 'center',
                'justify-content': 'center',
                'height': '100%',
                'width': '100%'}
        )
    return children


@app.callback(

    [
        Output("top_types_title", 'children'),
        Output("top_types", 'children'),
    ],
    [
        Input("checkboxes", 'value'),
    ]
)
def get_top_professions(checkboxes):
    checkboxes = set(checkboxes)
    length = 0
    if checkboxes:
        length = len(df[df['Требуемые области деятельности'].apply(
            lambda x: checkboxes.issubset(x.split(', ')))])
    if length:
        checkboxes = set(checkboxes)
        top_types = get_top_types(checkboxes)
        if len(top_types.split(', ')) > 1:
            top_types_title = 'Наиболее подходящие типы проектов для вас: '
        else:
            top_types_title = 'Наиболее подходящий тип проекта для вас: '
        return top_types_title, top_types
    else:
        return '', ''


@app.callback(
    Output('button_search', 'disabled'),
    [
        Input('button_anketa', 'children'),
        Input('button_test', 'children')
    ]
)
def get_button_search_enabled(button1, button2):
    if button1 == 'ДАЛЕЕ' == button2:
        return False
    else:
        return True


@app.callback(

    Output("search_table", 'children'),
    [
        Input("button_search", 'n_clicks'),
        Input('email-input', 'value')
    ]
)
def get_search_table(button, email):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'button_search' in changed_id:
        last_column = [
            html.Label(
                "Баллы совместимости",
                id="tooltip-target",
                style={"textDecoration": "underline", "cursor": "pointer", 'font-family': font_family},
            ),
            dbc.Tooltip(
                [
                    html.P(
                        'За совпадение группы/потока/института даётся по 1-му баллу, т.е. если человек из твоей группы, то ему присуждается +3 балла',
                        style={'font-family': font_family}
                    ),
                    html.Br(),
                    html.P(
                        'За каждое совпадение слов в колонках "Области деятельности" и "Подходящие типы проектов" присуждается по 1 баллу',
                        style={'font-family': font_family}
                    ),
                    html.Br(),
                    html.P(
                        'За совпадение каждого номера в столбце "Выбранные проекты" присуждается по 3 балла',
                        style={'font-family': font_family}
                    ),
                ],
                target="tooltip-target", placement='left', style={'text-align': 'left', 'font-family': font_family}
            ),
        ]

        columns = [
            *student_columns,
            last_column
        ]
        data = db.get_pandas()

        student_data = data.loc[email]
        data = data.dropna()

        data['Баллы совместимости'] = get_top_students(data, student_data)
        data.sort_values(by='Баллы совместимости', ascending=False, inplace=True)
        data['Выбранные проекты'] = data['Выбранные проекты'].apply(str)

        index = data.index.get_loc(email)
        if index:
            data.iloc[index], data.iloc[0] = data.iloc[0], data.iloc[index]

        width_iter = [5, 10, 5, 10, 10, 15, 15, 15, 5, 5, 5]

        table = dbc.Table(
            html.Table(className='table',
                       style={'width': '100%', 'height': '100%', 'font-size': 12}, children=
                       [
                           html.Thead(
                               [
                                   html.Tr(
                                       [
                                           html.Th(html.Label(column) if col != len(columns) - 1 else column,
                                                   style={'width': f'{width_iter[col]}%', }) for col, column in
                                           enumerate(columns)
                                       ], style={'fontWeight': 'bold', 'text-align': 'center'}
                                   )
                               ]
                           ),
                           html.Tbody(
                               [
                                   html.Tr(
                                       [
                                           html.Td(
                                               html.Div(
                                                   html.Img(src=data.iloc[row, 0]), style={'text-align': 'center'}
                                               ), style={'width': f'{width_iter[0]}%'}

                                           ),
                                           html.Td(
                                               [
                                                   html.P(data.iloc[row, 1].split(':')[0],
                                                          style={'text-align': 'center', 'font-family': font_family}),
                                                   html.P(
                                                       get_vk_name(data.iloc[row, 1], row), style={
                                                           'font-style': 'italic',
                                                           'font-size': 10,
                                                           'text-align': 'center'
                                                       }
                                                   )
                                               ],
                                               style={'width': f'{width_iter[1]}%'}
                                           ),
                                           html.Td(
                                               data.iloc[row, 2], style={
                                                   'width': f'{width_iter[2]}%', 'text-align': 'center'
                                               }
                                           ),
                                           html.Td(
                                               data.iloc[row, 3], style={
                                                   'width': f'{width_iter[3]}%', 'text-align': 'center'
                                               }
                                           ),
                                           html.Td(
                                               html.A(data.iloc[row, 4], href=f'//{data.iloc[row, 4]}',
                                                      target='_blank'),
                                               style={'width': f'{width_iter[4]}%'}
                                           ),
                                           html.Td(data.iloc[row, 5], style={'width': f'{width_iter[5]}%'}),
                                           html.Td(data.iloc[row, 6], style={'width': f'{width_iter[6]}%'}),
                                           html.Td(data.iloc[row, 7], style={'width': f'{width_iter[7]}%'}),
                                           html.Td(data.iloc[row, 8], style={'width': f'{width_iter[8]}%'}),
                                           html.Td('✅' if data.iloc[row, 9] else '❌',
                                                   style={'width': f'{width_iter[9]}%', 'text-align': 'center'}),
                                           html.Td(data.iloc[row, 10] if row else '',
                                                   style={
                                                       'width': f'{width_iter[10]}%',
                                                       'text-align': 'center',
                                                       'font-size': 16,
                                                       'fontWeight': 500,
                                                       'color': 'SteelBlue'
                                                   }
                                                   ),
                                       ]
                                   ) for row in range(len(data))
                               ]
                           ),
                       ]
                       ), bordered=True, responsive=True

        )
        return table
    return None


application = app.server
if not testing:
    server = app.server

if __name__ == '__main__':
    if not testing:
        # FOR ALIBABA CLOUD
        app.run_server(debug=False)
    else:
        # FOR AWS
        application.run(debug=True,
                        # host='0.0.0.0',
                        port=8080)
