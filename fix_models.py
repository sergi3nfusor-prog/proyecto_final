import re

with open('app/models.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix Column definitions: IDUsuarioEmpleado = db.Column(db.Integer...) -> IDUsuarioEmpleado = db.Column('idusuarioempleado', db.Integer...)
def replace_col(m):
    var_name = m.group(1)
    rest = m.group(2)
    return f"{var_name} = db.Column('{var_name.lower()}', {rest}"

text = re.sub(r'([a-zA-Z0-9_]+)\s*=\s*db\.Column\((db\.[A-Z][a-zA-Z0-9_]+)', replace_col, text)

# Fix ForeignKeys: db.ForeignKey("usuarioempleado.IDUsuarioEmpleado") -> db.ForeignKey("usuarioempleado.idusuarioempleado")
def replace_fk(m):
    table = m.group(1).lower()
    col = m.group(2).lower()
    return f"db.ForeignKey('{table}.{col}')"

text = re.sub(r'db\.ForeignKey\([\'"]([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[\'"]\)', replace_fk, text)

with open('app/models.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("models.py arreglado")
