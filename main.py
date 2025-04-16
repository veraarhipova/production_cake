from flask import Flask, request, render_template, redirect, url_for, flash, session
import mysql.connector
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='12345678',
        database='production_cake'
    )

import mysql.connector

# Установка соединения с базой данных
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345678",
    database="production_cake"
)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('client_full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')

        if not full_name or not email or not phone_number or not password:
            flash('Все поля должны быть заполнены!', 'error')
            return redirect(url_for('register'))

        try:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
                    if cursor.fetchone():
                        flash('Этот email уже зарегистрирован!', 'error')
                        return redirect(url_for('register'))

                    cursor.execute("INSERT INTO clients (client_full_name, email, client_phone_number, password) VALUES (%s, %s, %s, %s)",
                                   (full_name, email, phone_number, password))
                    connection.commit()

                    cursor.execute("SELECT id_client FROM clients WHERE email = %s", (email,))
                    client_id = cursor.fetchone()[0]
                    session['user_id'] = client_id  # Сохраняем ID клиента в сессии

                    flash('Регистрация прошла успешно!', 'success')
                    return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Ошибка базы данных: {err}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/cakes', methods=['GET'])
def cakes():
    # Получаем параметры сортировки, поиска и текущей страницы
    sort_option = request.args.get('sort', 'price')
    order = request.args.get('order', 'asc')
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    items_per_page = 6  # Количество записей на страницу

    # Устанавливаем колонку для сортировки
    column = 'cake_price' if sort_option == 'price' else 'cake_calorie'
    sort_order = 'ASC' if order == 'asc' else 'DESC'

    # Рассчитываем смещение
    offset = (page - 1) * items_per_page

    # Формируем запрос к базе данных
    base_query = f"SELECT id_cake, cake_name, cake_price, cake_calorie FROM menu"
    if search_query:
        base_query += f" WHERE cake_name LIKE %s"
    base_query += f" ORDER BY {column} {sort_order} LIMIT {items_per_page} OFFSET {offset}"

    # Задаем пути к изображениям для каждого торта вручную
    cake_images = {
        'Шоколадный торт': 'images/shokoladnyy_tort_cake.jpg',
        'Ванильный торт': 'images/vanilnyy_tort_cake.jpg',
        'Красный бархат': 'images/krasnyy_barhat_tort_cake.jpg',
        'Морковный торт': 'images/morkovnyy_tort_cake.jpg',
        'Чизкейк': 'images/chizkeyk_tort_cake.jpg',
        'Фруктовый торт': 'images/fruktovy_tort_cake.jpg',
        'Лимонный торт': 'images/limonnyy_tort_cake.jpg',
        'Кокосовый торт': 'images/kokosovy_tort_cake.jpg',
        'Наполеон': 'images/napoleon_tort_cake.jpg',
        'Медовик': 'images/medovik_tort_cake.jpg',
    }

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Получаем торты с учетом фильтров и пагинации
                if search_query:
                    cursor.execute(base_query, (f"%{search_query}%",))
                else:
                    cursor.execute(base_query)
                cakes = cursor.fetchall()

                # Добавляем путь к изображению для каждого торта
                for cake in cakes:
                    cake['image_path'] = cake_images.get(cake['cake_name'], 'images/default_cake.jpg')

                # Подсчитываем общее количество записей для пагинации
                count_query = "SELECT COUNT(*) AS total FROM menu"
                if search_query:
                    count_query += " WHERE cake_name LIKE %s"
                    cursor.execute(count_query, (f"%{search_query}%",))
                else:
                    cursor.execute(count_query)
                total_items = cursor.fetchone()['total']

    except mysql.connector.Error as err:
        flash(f'Ошибка базы данных: {err}', 'error')
        cakes = []
        total_items = 0

    # Рассчитываем общее количество страниц
    total_pages = (total_items + items_per_page - 1) // items_per_page

    return render_template(
        'cakes.html',
        cakes=cakes,
        sort_option=sort_option,
        order=order,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        cake_id = request.form.get('cake_id')
        quantity = request.form.get('quantity')

        # Проверка и преобразование данных
        cake_id = str(int(cake_id))  # Преобразуем cake_id в строку
        quantity = int(quantity) if quantity else 1  # Если quantity пустое, то 1 по умолчанию

        # Убедимся, что корзина существует и является словарем
        if 'cart' not in session or not isinstance(session['cart'], dict):
            session['cart'] = {}

        # Добавляем или обновляем количество товара в корзине
        if cake_id in session['cart']:
            session['cart'][cake_id] += quantity
        else:
            session['cart'][cake_id] = quantity

        session.modified = True
        flash("Торт добавлен в корзину!", "success")
    except (ValueError, TypeError) as e:
        flash(f"Ошибка при добавлении товара в корзину: {e}", "error")
        print("Ошибка:", e)

    return redirect(url_for('cart'))


def get_cake_by_id(cake_id):
    # Функция для извлечения данных о торте по ID из базы данных
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM menu WHERE id_cake = %s', (cake_id,))
    cake = cursor.fetchone()
    cursor.close()
    connection.close()
    return cake


@app.route('/cart')
def cart():
    # Получаем корзину из сессии и преобразуем в объект
    cart = session.get('cart', '{}')
    if isinstance(cart, str):
        cart = json.loads(cart)

    cake_details = {}
    total_price = 0

    for cake_id, quantity in cart.items():
        cake_id = int(cake_id)  # Преобразуем cake_id в int
        quantity = int(quantity)  # Преобразуем quantity в int

        # Получаем информацию о торте из базы данных
        cake = get_cake_by_id(cake_id)
        if cake:
            cake_details[cake_id] = {
                'name': cake['cake_name'],
                'price': cake['cake_price'],
                'quantity': quantity,
                'total': cake['cake_price'] * quantity
            }
            total_price += cake['cake_price'] * quantity

    return render_template('cart.html', cake_details=cake_details, total_price=total_price)


@app.route('/place_order', methods=['POST'])
def place_order():
    client_id = session.get('user_id')

    # Проверка на то, что пользователь вошел в систему
    if not client_id:
        flash('Сначала войдите в систему!', 'error')
        return redirect(url_for('login'))

    # Проверка на пустую корзину
    if 'cart' not in session or not session['cart']:
        flash("Ваша корзина пуста!", "error")
        return redirect(url_for('cart'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Создаем новый заказ
        admin_id = 1  # Пример фиксированного admin_id
        # Статус 0 - заказ оформлен, 1 - передан на производство
        cursor.execute(
            "INSERT INTO orders (id_client, order_status, order_date, id_admin) VALUES (%s, %s, NOW(), %s)",
            (client_id, 0, admin_id))  # Статус 0 - заказ оформлен

        order_id = cursor.lastrowid  # Получаем ID нового заказа

        # Добавляем товары из корзины в таблицу shopping_cart
        for cake_id, quantity in session['cart'].items():  # Используем session['cart'] напрямую
            cursor.execute('''
                INSERT INTO shopping_cart (id_order, id_cake, cake_quantity)
                VALUES (%s, %s, %s)
            ''', (order_id, cake_id, quantity))

        connection.commit()

        # Очищаем корзину
        session.pop('cart', None)

    except mysql.connector.Error as err:
        flash(f"Ошибка базы данных: {err}", "error")
        print(f"Ошибка базы данных: {err}")
    finally:
        cursor.close()
        connection.close()

    # Перенаправляем на страницу с заказами
    return redirect(url_for('client_orders'))  # Перенаправление на страницу с заказами клиента

@app.route('/update_cart', methods=['POST'])
def update_cart():
    try:
        # Получаем данные и проверяем их
        cake_id = request.form.get('cake_id')
        quantity = request.form.get('quantity')

        cake_id = str(int(cake_id))  # Преобразуем cake_id в строку
        quantity = int(quantity) if quantity is not None else 1

        # Убедимся, что корзина существует и является словарем
        if 'cart' in session and isinstance(session['cart'], dict):
            # Обновляем или удаляем товар в зависимости от количества
            if quantity > 0:
                session['cart'][cake_id] = quantity
            else:
                session['cart'].pop(cake_id, None)  # Удаляем товар, если количество 0
            session.modified = True
            flash("Количество товара обновлено!", "success")
        else:
            flash("Ошибка: Товар не найден в корзине.", "error")
    except (ValueError, TypeError) as e:
        flash(f"Ошибка при обновлении корзины: {e}", "error")
        print("Ошибка:", e)

    return redirect(url_for('cart'))


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/client_orders')
def client_orders():
    client_id = session.get('user_id')  # Получаем client_id из session
    if not client_id:
        flash('Сначала войдите в систему!', 'error')
        return redirect(url_for('login'))

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('''
                    SELECT id_order,
                           CASE
                               WHEN order_status = 0 THEN 'Заказ оформлен'
                               WHEN order_status = 1 THEN 'Передан на производство'
                               ELSE 'Неизвестный статус'
                           END AS order_status,
                           order_date
                    FROM orders
                    WHERE id_client = %s  -- Фильтруем заказы по id клиента
                    ORDER BY order_date DESC
                ''', (client_id,))
                orders = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Ошибка базы данных: {err}', 'error')
        orders = []

    return render_template('client_orders.html', orders=orders)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Проверяем в таблице admins
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
                admin = cursor.fetchone()

                if admin and admin['password'] == password:
                    session['user_id'] = admin['id_admin']
                    session['role'] = 'admin'
                    flash('Добро пожаловать, администратор!', 'success')
                    return redirect(url_for('admin_dashboard'))

                # Проверяем в таблице clients
                cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
                client = cursor.fetchone()

                if client and client['password'] == password:
                    session['user_id'] = client['id_client']  # Сохраняем ID клиента
                    session['role'] = 'client'
                    flash('Добро пожаловать!', 'success')
                    return redirect(url_for('cakes'))

        flash('Неправильная электронная почта или пароль.', 'error')

    return render_template('login.html')


from functools import wraps

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped_view(**kwargs):
            if 'user_id' not in session:
                flash('Необходимо войти в систему', 'error')
                return redirect(url_for('client_login'))
            if role and session.get('role') != role:
                flash('Недостаточно прав доступа', 'error')
                return redirect(url_for('client_login'))
            return f(**kwargs)
        return wrapped_view
    return decorator

import mysql.connector


@app.route('/admin_dashboard')
def admin_dashboard():
    try:
        # Подключение к базе данных
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]  # Читаем все строки
    except mysql.connector.Error as err:
        flash(f"Ошибка при загрузке таблиц: {err}", "error")
        tables = []

    return render_template('admin_dashboard.html', tables=tables)


@app.route('/admin_tables')
def admin_tables():
    try:
        # Подключение к базе данных
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")  # Получаем все таблицы в базе данных
                tables = [row[0] for row in cursor.fetchall()]  # Преобразуем в список названий таблиц
    except Exception as e:
        flash(f'Ошибка при получении данных о таблицах: {e}', 'error')
        tables = []

    return render_template('admin_tables.html', tables=tables)  # Передаем данные в шаблон


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            with get_db_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
                    admin = cursor.fetchone()

                    if admin and admin['password'] == password:  # Без хэширования
                        # Устанавливаем значения в сессии
                        session['user_id'] = admin['id_admin']
                        session['role'] = 'admin'
                        flash('Добро пожаловать, администратор!', 'success')
                        return redirect(url_for('admin_orders'))  # Перенаправление на страницу заказов администратора

                    flash('Неправильный email или пароль', 'danger')

        except Exception as e:
            flash(f'Ошибка: {e}', 'error')

    return render_template('admin_login.html')

@app.route('/admin_orders')
def admin_orders():
    if 'role' not in session or session['role'] != 'admin':
        flash('Вы не авторизованы как администратор!', 'error')
        return redirect(url_for('admin_login'))

    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT * FROM orders ORDER BY order_date DESC')
                orders = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Ошибка базы данных: {err}', 'error')
        orders = []

    return render_template('admin_orders.html', orders=orders)



# Главная страница для администратора
@app.route('/admin')
def admin_home():
    cursor = db.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    return render_template('admin_tables.html', tables=tables)


@app.route('/admin_table/<table_name>', methods=['GET'])
def admin_table_view(table_name):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Получаем названия колонок
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = cursor.fetchall()
                column_names = [col['Field'] for col in columns]

                # Определяем уникальный идентификатор
                primary_key_column = next((col for col in column_names if col.startswith('id')), None)

                # Загружаем данные таблицы
                cursor.execute(f"SELECT * FROM {table_name}")
                data = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Ошибка базы данных: {err}", "error")
        return redirect(url_for('admin_dashboard'))

    return render_template(
        'admin_table.html',
        table_name=table_name,
        data=data,
        primary_key_column=primary_key_column
    )


@app.route('/admin_table/<table_name>/delete/<int:entry_id>', methods=['POST'])
def delete_entry(table_name, entry_id):
    try:
        # Проверяем, какой уникальный идентификатор используется в таблице
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = [column['Field'] for column in cursor.fetchall()]

                # Определяем имя идентификатора
                id_column = next((col for col in columns if col.startswith('id')), None)

                if not id_column:
                    flash("Удаление невозможно: в таблице нет уникального идентификатора.", "error")
                    return redirect(url_for('admin_table_view', table_name=table_name))

                # Удаляем запись
                query = f"DELETE FROM {table_name} WHERE {id_column} = %s"
                cursor.execute(query, (entry_id,))
                connection.commit()
                flash(f"Запись с {id_column} = {entry_id} успешно удалена.", "success")
    except mysql.connector.Error as err:
        flash(f"Ошибка при удалении записи: {err}", "error")

    return redirect(url_for('admin_table_view', table_name=table_name))


# Добавление записи
@app.route('/admin_table/<table_name>/add', methods=['GET', 'POST'])
def add_entry(table_name):
    if request.method == 'POST':
        data = request.form.to_dict()
        keys = ', '.join(data.keys())
        values = ', '.join(f"'{v}'" for v in data.values())
        cursor = db.cursor()
        try:
            query = f"INSERT INTO {table_name} ({keys}) VALUES ({values})"
            cursor.execute(query)
            db.commit()
            flash("Запись успешно добавлена!", "success")
        except Exception as e:
            flash(f"Ошибка при добавлении записи: {e}", "danger")
        finally:
            cursor.close()
        return redirect(url_for('admin_table_view', table_name=table_name))
    else:
        cursor = db.cursor()
        try:
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [column[0] for column in cursor.fetchall()]
        except Exception as e:
            flash(f"Ошибка при получении структуры таблицы: {e}", "danger")
            columns = []
        finally:
            cursor.close()
        return render_template('add_entry.html', table_name=table_name, columns=columns)


@app.route('/admin_table/<table_name>/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(table_name, entry_id):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                # Получаем названия колонок
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = cursor.fetchall()
                column_names = [col['Field'] for col in columns]

                # Загружаем данные для редактирования
                cursor.execute(f"SELECT * FROM {table_name} WHERE {column_names[0]} = %s", (entry_id,))
                data = cursor.fetchone()

                if request.method == 'POST':
                    # Собираем данные для обновления
                    updated_data = {}
                    for column in column_names:
                        updated_data[column] = request.form.get(column)

                    # Строим SQL запрос для обновления
                    set_clause = ", ".join([f"{col} = %s" for col in column_names if col != column_names[0]])
                    values = [updated_data[col] for col in column_names if col != column_names[0]]
                    values.append(entry_id)  # ID для WHERE

                    update_query = f"UPDATE {table_name} SET {set_clause} WHERE {column_names[0]} = %s"
                    cursor.execute(update_query, values)
                    connection.commit()

                    flash("Запись успешно обновлена!", "success")
                    return redirect(url_for('admin_table_view', table_name=table_name))

    except mysql.connector.Error as err:
        flash(f"Ошибка базы данных: {err}", "error")
        return redirect(url_for('admin_table_view', table_name=table_name))

    return render_template('edit_entry.html', table_name=table_name, data=data, column_names=column_names)

if __name__ == "__main__":
    app.run(debug=False, port=5002)  # debug=False - отключаем режим отладки
