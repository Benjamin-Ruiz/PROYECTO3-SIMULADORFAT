import os 
import json
from datetime import datetime
import uuid

# --- CONFIGURACION BASICA ---
DB_DIR = "db"                       # Carpeta base donde se guarda todo
FAT_DIR = os.path.join(DB_DIR, "fat")       # Carpeta donde se guardan las tablas FAT
BLOCKS_DIR = os.path.join(DB_DIR, "blocks") # Carpeta donde se guardan los bloques de datos
TAM_BLOQUE = 20                     # Hasta 20 caracteres

# Crea las carpetas si no existen
os.makedirs(FAT_DIR, exist_ok=True)
os.makedirs(BLOCKS_DIR, exist_ok=True)

#--------------FUNCIONES JSON---------------------
#Lee un archivo JSON desde una ruta y devuelve su contenido como diccionario
def leer_json(ruta):
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)
#Guarda un diccionario en un archivo JSON con formato legible
def escribir_json(ruta, data):
    
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

#-----------------FUNCIONES DE TIEMPO Y RUTA---------------


#Devuelve la fecha y hora actual como texto.
def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def ruta_fat(nombre_archivo):
    nombre_limpio = nombre_archivo.replace("/", "_").replace("\\", "_")
    return os.path.join(FAT_DIR, f"{nombre_limpio}.json")
def ruta_bloque(id_bloque):
    return os.path.join(BLOCKS_DIR, f"{id_bloque}.json")

#-----------------------GESTION DE PERMISOS---------------

#Verifica si el usuario tiene permiso de lectura en el archivo.
def tiene_permiso_lectura(fat, usuario):
    if usuario == fat["owner"]:  
        return True
    perms = fat.get("permisos", {})
    u = perms.get(usuario, {})
    return bool(u.get("lectura", False))

#Verifica si el usuario tiene permiso de escritura en el archivo.
def tiene_permiso_escritura(fat, usuario):
    if usuario == fat["owner"]:
        return True
    perms = fat.get("permisos", {})
    u = perms.get(usuario, {})
    return bool(u.get("escritura", False))

#-------------------------------BLOQUES------------------------------

def crear_cadena_bloques(contenido):
    if contenido is None:
        contenido = ""
    partes = [contenido[i:i+TAM_BLOQUE] for i in range(0, len(contenido), TAM_BLOQUE)]
    if len(partes) == 0:
        partes = [""]

    primer_id = None
    anterior_id = None
# Genera un identificador unico para cada bloque
    for i, pedazo in enumerate(partes):
        bloque_id = str(uuid.uuid4())  
        bloque = {
            "datos": pedazo,
            "siguiente": None,
            "eof": False
        }
        if anterior_id is not None:
            ruta_ant = ruta_bloque(anterior_id)
            ant = leer_json(ruta_ant)
            ant["siguiente"] = bloque_id
            escribir_json(ruta_ant, ant)
        else:
            primer_id = bloque_id  
        if i == len(partes) - 1:
            bloque["eof"] = True

        escribir_json(ruta_bloque(bloque_id), bloque)
        anterior_id = bloque_id

    return primer_id
#LECTOR DESDE EL ID PRINCIPAL Y RETORNO COMPLETO DE TEXTO Y LISTA DE IDS DE LOS BLOQUES USADOS
def leer_cadena_bloques(primer_id):
    texto = ""
    ids = []
    actual = primer_id
    visitados = set()

    while actual and actual not in visitados:
        visitados.add(actual)
        ids.append(actual)
        ruta = ruta_bloque(actual)
        data = leer_json(ruta)
        if not data:
            break
        texto += data.get("datos", "")
        if data.get("eof", False): 
            break
        actual = data.get("siguiente", None)
    return texto, ids

#ELIMINACION FISICA DE LOS BLOQUES DE DATOS EN EL DISCO
def eliminar_cadena_bloques(primer_id):
    _, ids = leer_cadena_bloques(primer_id)
    for bid in ids:
        try:
            os.remove(ruta_bloque(bid))
        except:
            pass
# -----------------------OPERACIONES FAT----------------------
#CREACION DE ARCHIVOS FAT CON METADATOS Y PERMISOS Y SE DIVIDE EL CONTENIDO EN BLOQUES
def crear_archivo_fat(nombre_archivo, contenido, owner):
    fpath = ruta_fat(nombre_archivo)
    if os.path.exists(fpath):
        print("Ya existe un archivo con ese nombre.")
        return

    primer_bloque_id = crear_cadena_bloques(contenido)
    fat = {
        "nombre": nombre_archivo,
        "ruta_datos_inicial": primer_bloque_id,
        "papelera": False,
        "tamano_total": len(contenido),
        "fecha_creacion": ahora(),
        "fecha_modificacion": None,
        "fecha_eliminacion": None,
        "owner": owner,         
        "permisos": {}           
    }
    escribir_json(fpath, fat)
    print("Archivo creado correctamente.")

#MUESTRA ARCVHIOS QUE NO ESTAN EN PAPELERA
def listar_archivos():
    
    archivos = []
    for fname in os.listdir(FAT_DIR):
        if fname.endswith(".json"):
            fat = leer_json(os.path.join(FAT_DIR, fname))
            if fat and not fat.get("papelera", False):
                archivos.append(fat["nombre"])
    if not archivos:
        print("No hay archivos (o todos estan en papelera).")
    else:
        print("Archivos disponibles:")
        for a in archivos:
            print(" -", a)

#ARCHIVOS QUE ESTAN EN LA PAPELERA
def listar_papelera():
    
    archivos = []
    for fname in os.listdir(FAT_DIR):
        if fname.endswith(".json"):
            fat = leer_json(os.path.join(FAT_DIR, fname))
            if fat and fat.get("papelera", False):
                archivos.append(fat["nombre"])
    if not archivos:
        print("Papelera vacia.")
    else:
        print("En papelera:")
        for a in archivos:
            print(" -", a)

#ABRE UN ARCHIVO Y MUESTRA METADATOS Y PERMISOS OTORGADOS
def abrir_archivo(nombre_archivo, usuario):
    
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if fat.get("papelera", False):
        print("Ese archivo esta en la papelera. (Recuperalo para abrirlo normalmente)")
        return
    if not tiene_permiso_lectura(fat, usuario):
        print("No tienes permiso de LECTURA para abrir este archivo.")
        return

    # MOSTRAR LOS METADATOS
    print("=== METADATOS ===")
    print("Nombre:", fat["nombre"])
    print("Owner:", fat["owner"])
    print("Tamano (caracteres):", fat["tamano_total"])
    print("Creacion:", fat["fecha_creacion"])
    print("Modificacion:", fat["fecha_modificacion"])
    print("Eliminacion:", fat["fecha_eliminacion"])
    print("En papelera:", fat["papelera"])
    print("Permisos:", fat.get("permisos", {}))

    # MSTRAR EL CONTENIDO DEL ARCHIVO
    print("\n=== CONTENIDO ===")
    texto, _ = leer_cadena_bloques(fat["ruta_datos_inicial"])
    print(texto)

#PERMITE MODIFICAR EL CONTENIDO DEL ARCHIVO
def modificar_archivo(nombre_archivo, usuario):
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if fat.get("papelera", False):
        print("El archivo esta en la papelera. Recuperalo antes de modificar.")
        return
    if not tiene_permiso_escritura(fat, usuario):
        print("No tienes permiso de ESCRITURA para modificar este archivo.")
        return

    # MOSTRAR CONETNIDO ACTUAL
    actual, _ = leer_cadena_bloques(fat["ruta_datos_inicial"])
    print("=== CONTENIDO ACTUAL ===")
    print(actual)

    # SE PIDE NUEVO CONTENIDO
    print("\nEscribe el NUEVO contenido (linea unica).")
    nuevo = input("Nuevo contenido: ")

    # CREACION DE NUEVOS BLOQUES Y ELIMINACION DE LOS ANTERIORES
    viejo_primer = fat["ruta_datos_inicial"]
    nuevo_primer = crear_cadena_bloques(nuevo)

    fat["ruta_datos_inicial"] = nuevo_primer
    fat["tamano_total"] = len(nuevo)
    fat["fecha_modificacion"] = ahora()
    escribir_json(fpath, fat)

    eliminar_cadena_bloques(viejo_primer)
    print("Archivo modificado correctamente.")

#MUEVE UN ARCHIVO A PAPELERA PERO NO BORRA FISICAMENTE LOS BLOQUES
def eliminar_archivo(nombre_archivo, usuario):
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if not tiene_permiso_escritura(fat, usuario):
        print("No tienes permiso para eliminar este archivo.")
        return
    if fat.get("papelera", False):
        print("Ya esta en la papelera.")
        return

    fat["papelera"] = True
    fat["fecha_eliminacion"] = ahora()
    escribir_json(fpath, fat)
    print("Archivo movido a la papelera.")
#RECUPERACION DE ARCHIVOS DE LA PAPELERA
def recuperar_archivo(nombre_archivo, usuario):
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if usuario != fat["owner"]:
        print("Solo el OWNER puede recuperar el archivo.")
        return
    if not fat.get("papelera", False):
        print("El archivo no esta en papelera.")
        return
    fat["papelera"] = False
    escribir_json(fpath, fat)
    print("Archivo recuperado.")
#ASIGNA PERMISOS DE LECTURA/ESCRITURA PARA OTRO USUARIUO
# Modificar la función asignar_permiso
def asignar_permiso(nombre_archivo, owner, usuario_objetivo, lectura, escritura):
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if owner != fat["owner"]:
        print("Solo el OWNER puede asignar o quitar permisos.")
        return
    if usuario_objetivo == fat["owner"]:
        print("El OWNER ya tiene todos los permisos.")
        return

    fat.setdefault("permisos", {})
    fat["permisos"][usuario_objetivo] = {
        "lectura": bool(lectura),
        "escritura": bool(escritura)
    }
    fat["fecha_modificacion"] = ahora()
    escribir_json(fpath, fat)
    print(f"Permisos actualizados para '{usuario_objetivo}'. (L:{lectura}, E:{escritura})")



#ELIMINA LOS PERMISOS SOBRE USUARIOS QUE NO SEAN EL OWNER
def revocar_permiso(nombre_archivo, owner, usuario_objetivo):
    fpath = ruta_fat(nombre_archivo)
    fat = leer_json(fpath)
    if not fat:
        print("No existe ese archivo.")
        return
    if owner != fat["owner"]:
        print("Solo el OWNER puede quitar permisos.")
        return
    if usuario_objetivo == fat["owner"]:
        print("No puedes revocar al OWNER.")
        return

    perms = fat.get("permisos", {})
    if usuario_objetivo in perms:
        del perms[usuario_objetivo]
        fat["permisos"] = perms
        fat["fecha_modificacion"] = ahora()
        escribir_json(fpath, fat)
        print(f"Permisos revocados a '{usuario_objetivo}'.")
    else:
        print("Ese usuario no tiene permisos asignados.")


#-------------MENU PRINCIPAL-----------------------

def menu():
    print("\n=== PROYECTO FAT ===")
    print("1. Crear archivo")
    print("2. Listar archivos")
    print("3. Mostrar papelera")
    print("4. Abrir archivo")
    print("5. Modificar archivo")
    print("6. Eliminar archivo (mover a papelera)")
    print("7. Recuperar archivo")
    print("8. Asignar permisos (owner)")
    print("9. Revocar permisos (owner)")
    print("0. Salir")
def main():
    print("SISTEMA FAT SIMULADO")
    usuario_actual = input("Ingresa tu nombre de usuario (sin espacios): ").strip()
    if not usuario_actual:
        usuario_actual = "usuario"

    while True:
        menu()
        op = input("Elige una opcion: ").strip()

        if op == "1":
            nombre = input("Nombre del archivo (sin extension): ").strip()
            print("Escribe el contenido en UNA SOLA LINEA:")
            contenido = input("> ")
            crear_archivo_fat(nombre, contenido, owner=usuario_actual)

        elif op == "2":
            listar_archivos()

        elif op == "3":
            listar_papelera()

        elif op == "4":
            nombre = input("Nombre del archivo a abrir: ").strip()
            abrir_archivo(nombre, usuario_actual)

        elif op == "5":
            nombre = input("Nombre del archivo a modificar: ").strip()
            modificar_archivo(nombre, usuario_actual)

        elif op == "6":
            nombre = input("Nombre del archivo a eliminar (papelera): ").strip()
            eliminar_archivo(nombre, usuario_actual)

        elif op == "7":
            nombre = input("Nombre del archivo a recuperar: ").strip()
            recuperar_archivo(nombre, usuario_actual)

        elif op == "8":
            nombre = input("Archivo donde asignar permisos: ").strip()
            usuario_objetivo = input("Usuario a asignar: ").strip()
            l = input("¿Permiso de lectura? (s/n): ").strip().lower() == "s"
            e = input("¿Permiso de escritura? (s/n): ").strip().lower() == "s"
            asignar_permiso(nombre, owner=usuario_actual, usuario_objetivo=usuario_objetivo, lectura=l, escritura=e)

        elif op == "9":
            nombre = input("Archivo donde revocar permisos: ").strip()
            usuario_objetivo = input("Usuario a revocar: ").strip()
            revocar_permiso(nombre, owner=usuario_actual, usuario_objetivo=usuario_objetivo)

        elif op == "0":
            print("Saliendo...")
            break
        else:
            print("Opcion invalida.")
if __name__ == "__main__":
    main()