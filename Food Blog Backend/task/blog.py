import sqlite3
import argparse
from collections import Counter


class FoodBlog:
    def __init__(self):
        self.conn = None
        self.cur = None

    def connect_db(self, db):
        self.conn = sqlite3.connect(db)
        self.cur = self.conn.cursor()

    def setup_db(self):
        try:
            self.cur.execute("PRAGMA foreign_keys = ON")

            self.cur.execute("""CREATE TABLE meals (
                                    meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    meal_name TEXT NOT NULL UNIQUE
                                    );""")

            self.cur.execute("""CREATE TABLE ingredients (
                                    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    ingredient_name TEXT NOT NULL UNIQUE
                                    );""")

            self.cur.execute("""CREATE TABLE measures (
                                    measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    measure_name TEXT UNIQUE
                                    );""")

            self.cur.execute("""CREATE TABLE recipes (
                                    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    recipe_name TEXT NOT NULL,
                                    recipe_description TEXT
                                    );""")

            self.cur.execute("""CREATE TABLE serve (
                                    serve_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    recipe_id INTEGER NOT NULL,
                                    meal_id INTEGER NOT NULL,
                                    CONSTRAINT fk_recipes FOREIGN KEY (recipe_id)
                                    REFERENCES recipes(recipe_id)
                                    CONSTRAINT fk_meals FOREIGN KEY (meal_id)
                                    REFERENCES meals(meal_id)
                                    );""")

            self.cur.execute("""CREATE TABLE quantity (
                                    quantity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    quantity INTEGER NOT NULL,
                                    measure_id INTEGER NOT NULL,
                                    ingredient_id INTEGER NOT NULL,
                                    recipe_id INTEGER NOT NULL,
                                    CONSTRAINT fk_measures FOREIGN KEY (measure_id)
                                    REFERENCES measures(measure_id)
                                    CONSTRAINT fk_ingredients FOREIGN KEY (ingredient_id)
                                    REFERENCES ingredients(ingredient_id)
                                    CONSTRAINT fk_recipes FOREIGN KEY (recipe_id)
                                    REFERENCES recipes(recipe_id)
                                    );""")

            self.conn.commit()
        except sqlite3.OperationalError:
            self.cur.execute("DELETE FROM meals")
            self.cur.execute("DELETE FROM ingredients")
            self.cur.execute("DELETE FROM measures")
            self.cur.execute("DELETE FROM recipes")
            self.cur.execute("DELETE FROM serve")
            self.cur.execute("DELETE FROM quantity")
            self.conn.commit()

    def populate_tables(self):
        self.cur.execute("INSERT INTO meals (meal_name)"
                         "VALUES ('breakfast'), ('brunch'), ('lunch'), ('supper');")

        self.cur.execute("INSERT INTO ingredients (ingredient_name)"
                         "VALUES ('milk'), ('cacao'), ('strawberry'), ('blueberry'), ('blackberry'), ('sugar');")

        self.cur.execute("INSERT INTO measures (measure_name)"
                         "VALUES ('ml'), ('g'), ('l'), ('cup'), ('tbsp'), ('tsp'), ('dsp'), ('');")

        self.conn.commit()

    def get_recipes(self):
        while True:
            print("Pass the empty recipe name to exit.")
            recipe_name = input("Recipe name: ")

            if recipe_name == "":
                self.conn.close()
                return
            else:
                recipe_description = input("Recipe description: ")
                print("1) breakfast  2) brunch  3) lunch  4) supper")
                meal_ids = input("Enter proposed meals separated by a space: ").split()
                self.save_recipe(recipe_name, recipe_description, meal_ids)

    def save_recipe(self, recipe_name, recipe_description, meal_ids):
        try:
            recipe_id = self.cur.execute("INSERT INTO recipes (recipe_name, recipe_description)"
                                         f"VALUES ('{recipe_name}', '{recipe_description}');").lastrowid
            for meal_id in meal_ids:
                self.cur.execute("INSERT INTO serve (recipe_id, meal_id)"
                                 f"VALUES ({recipe_id}, {int(meal_id)});")

            while True:
                answer = input("Input quantity of ingredient <press enter to stop>: ").split()

                if not answer:
                    break

                self.cur.execute(f"SELECT ingredient_id FROM ingredients WHERE ingredient_name LIKE '%{answer[-1]}%';")

                ingredient_id = self.cur.fetchall()

                if len(ingredient_id) > 1:
                    print("The measure is not conclusive!")
                    continue

                self.cur.execute(f"SELECT measure_id FROM measures WHERE measure_name LIKE '{answer[1] + '%' if len(answer) == 3 else ''}';")

                measure_id = self.cur.fetchall()

                if len(measure_id) > 1:
                    print("The measure is not conclusive!")
                    continue

                self.cur.execute(f"INSERT INTO quantity (quantity, recipe_id, measure_id, ingredient_id) VALUES ({int(answer[0])}, {recipe_id}, {measure_id[0][0]}, {ingredient_id[0][0]});")
        except sqlite3.IntegrityError:
            pass

        self.conn.commit()

    def query_meals(self, arguments):
        self.cur.execute(f"SELECT ingredient_id "
                         f"FROM ingredients "
                         f"WHERE '{arguments.ingredients}' LIKE '%' || ingredient_name || '%';")
        ingredient_ids = [x[0] for x in self.cur.fetchall()]
        str_ingredient_ids = list(map(str, ingredient_ids))

        self.cur.execute(f"SELECT meal_id "
                         f"FROM meals "
                         f"WHERE '{arguments.meals}' LIKE '%' || meal_name || '%';")
        meal_ids = [x[0] for x in self.cur.fetchall()]
        str_meal_ids = list(map(str, meal_ids))

        self.cur.execute(f"SELECT recipe_id "
                         f"FROM quantity "
                         f"WHERE ingredient_id IN ({','.join(str_ingredient_ids)});")
        recipe_ingredient_ids = [x[0] for x in self.cur.fetchall()]
        results = []
        for recipe_id, count in Counter(recipe_ingredient_ids).items():
            if count == len(arguments.ingredients.split(',')):
                self.cur.execute(f"SELECT recipe_id "
                                 f"FROM serve "
                                 f"WHERE recipe_id = {recipe_id} and meal_id IN({','.join(str_meal_ids)})")

                recipe_ids = [x[0] for x in self.cur.fetchall()]
                if recipe_ids is not None:
                    results.append(recipe_id)
        results = list(map(str, results))
        self.cur.execute(f"SELECT recipe_name "
                         f"FROM recipes "
                         f"WHERE recipe_id IN ({','.join(results)})")

        recipe_names = self.cur.fetchall()

        print(recipe_names if len(recipe_names) != 0 else 'no such recipes')

        self.conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('db', help="DB filename for connection.")
    parser.add_argument("-i", "--ingredients", help="Comma separated list of ingredients.")
    parser.add_argument("-m", "--meals", help="Comma separated list of meals")
    args = parser.parse_args()

    blog = FoodBlog()
    if args.ingredients is None and args.meals is None:
        blog.connect_db(args.db)
        blog.setup_db()
        blog.populate_tables()
        blog.get_recipes()
    else:
        blog.connect_db(args.db)
        blog.query_meals(args)
