from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from db_connection import get_db
from pydantic import BaseModel
import datetime
import os
import uuid
from typing import Optional
import os
import uuid
from pathlib import Path
import aiofiles

router = APIRouter()
# Configuración flexible
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = os.path.join(BASE_DIR, "static")  # Ruta por defecto

# Compatibilidad con código existente
POST_IMAGES_DIR = os.path.join(IMAGE_DIR, "posts")  # /app/static/posts
PROFILE_IMAGES_DIR = os.path.join(IMAGE_DIR, "profiles")  # /app/static/profiles


# MODELOS Pydantic
class Usuario(BaseModel):
    nombre: str
    email: str
    contraseña: str
    tipo_usuario: str
    codigo_postal: Optional[str] = None
    foto_usuario: Optional[str] = None

class Mascota(BaseModel):
    nombre: str
    especie: str
    raza: Optional[str] = None
    edad: int
    id_usuario: int

class Publicacion(BaseModel):
    id_usuario: int
    contenido: str
    foto_publicacion: Optional[str] = None

class Comentario(BaseModel):
    id_publicacion: int
    id_usuario: int
    contenido: str

class Mensaje(BaseModel):
    id_emisor: int
    id_receptor: int
    contenido: str

class Adopcion(BaseModel):
    id_mascota: int
    id_usuario_adoptante: int
    fecha_adopcion: datetime.date

class MeGusta(BaseModel):
    id_publicacion: int
    id_usuario: int

class Categoria(BaseModel):
    nombre: str

class Producto(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    imagen: Optional[str] = None
    id_usuario_empresa: int
    id_categoria: int
    link_externo: Optional[str] = None

# FUNCIONES AUXILIARES
async def save_image(file: UploadFile, directory: str = None) -> str:
    """Versión flexible que funciona con y sin directorio específico"""
    target_dir = directory if directory else IMAGE_DIR
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    file_ext = file.filename.split('.')[-1].lower()
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(target_dir, filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as buffer:
            await buffer.write(await file.read())
        
        print(f"✅ Imagen guardada en: {file_path}")
        return filename
    except Exception as e:
        print(f"❌ Error al guardar imagen: {str(e)}")
        raise

# ENDPOINTS PARA IMÁGENES
@router.post("/upload/profile/{user_id}")
async def upload_profile_image(
    user_id: int,
    file: UploadFile = File(...)
):
    """Subir foto de perfil"""
    try:
        filename = await save_image(file, PROFILE_IMAGES_DIR)
        
        conn = get_db()
        cursor = conn.cursor()
        query = "UPDATE Usuarios SET foto_usuario = %s WHERE id_usuario = %s"
        cursor.execute(query, (filename, user_id))
        conn.commit()
        
        return {
            "status": "success",
            "image_url": f"/{PROFILE_IMAGES_DIR}/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/post/{post_id}")
async def upload_post_image(
    post_id: int,
    file: UploadFile = File(...)
):
    """Subir foto de publicación"""
    try:
        filename = await save_image(file, POST_IMAGES_DIR)
        
        conn = get_db()
        cursor = conn.cursor()
        query = "UPDATE Publicaciones SET foto_publicacion = %s WHERE id_publicacion = %s"
        cursor.execute(query, (filename, post_id))
        conn.commit()
        
        return {
            "status": "success",
            "image_url": f"/{POST_IMAGES_DIR}/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ENDPOINTS PARA USUARIOS
@router.post("/usuarios/")
async def crear_usuario(
    nombre: str = Form(...),
    email: str = Form(...),
    contraseña: str = Form(...),
    tipo_usuario: str = Form(...),
    codigo_postal: Optional[str] = Form(None),
    foto_usuario: Optional[UploadFile] = File(None)
):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    foto_filename = None
    if foto_usuario:
        foto_filename = await save_image(foto_usuario, PROFILE_IMAGES_DIR)
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Usuarios 
        (nombre, email, contraseña, tipo_usuario, codigo_postal, foto_usuario) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        nombre, email, contraseña, tipo_usuario, 
        codigo_postal, foto_filename
    ))
    conn.commit()
    
    return {"mensaje": "Usuario creado correctamente"}

@router.get("/usuarios/{id_usuario}")
def obtener_usuario(id_usuario: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Usuarios WHERE id_usuario = %s"
    cursor.execute(query, (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return usuario

@router.put("/usuarios/{id_usuario}")
async def actualizar_usuario(
    id_usuario: int,
    nombre: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    contraseña: Optional[str] = Form(None),
    tipo_usuario: Optional[str] = Form(None),
    codigo_postal: Optional[str] = Form(None),
    foto_usuario: Optional[UploadFile] = File(None)
):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Usuarios WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_fields = {}
    if nombre: update_fields['nombre'] = nombre
    if email: update_fields['email'] = email
    if contraseña: update_fields['contraseña'] = contraseña
    if tipo_usuario: update_fields['tipo_usuario'] = tipo_usuario
    if codigo_postal: update_fields['codigo_postal'] = codigo_postal
    
    if foto_usuario:
        foto_filename = await save_image(foto_usuario, PROFILE_IMAGES_DIR)
        update_fields['foto_usuario'] = foto_filename
    
    if update_fields:
        set_clause = ", ".join([f"{k} = %s" for k in update_fields])
        values = list(update_fields.values())
        values.append(id_usuario)
        
        query = f"UPDATE Usuarios SET {set_clause} WHERE id_usuario = %s"
        cursor.execute(query, values)
        conn.commit()
    
    return {"mensaje": "Usuario actualizado correctamente"}

@router.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Usuarios WHERE id_usuario = %s"
    cursor.execute(query, (id_usuario,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Usuario eliminado correctamente"}

# ENDPOINTS PARA MASCOTAS
@router.post("/mascotas/")
def crear_mascota(mascota: Mascota):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Mascotas 
        (nombre, especie, raza, edad, id_usuario) 
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        mascota.nombre, mascota.especie, 
        mascota.raza, mascota.edad, mascota.id_usuario
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Mascota creada correctamente"}

@router.get("/mascotas/{id_mascota}")
def obtener_mascota(id_mascota: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Mascotas WHERE id_mascota = %s"
    cursor.execute(query, (id_mascota,))
    mascota = cursor.fetchone()
    cursor.close()
    conn.close()

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return mascota

@router.put("/mascotas/{id_mascota}")
def actualizar_mascota(id_mascota: int, mascota: Mascota):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        UPDATE Mascotas 
        SET nombre = %s, especie = %s, raza = %s, edad = %s 
        WHERE id_mascota = %s
    """
    cursor.execute(query, (
        mascota.nombre, mascota.especie, 
        mascota.raza, mascota.edad, id_mascota
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Mascota actualizada correctamente"}

@router.delete("/mascotas/{id_mascota}")
def eliminar_mascota(id_mascota: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Mascotas WHERE id_mascota = %s"
    cursor.execute(query, (id_mascota,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Mascota eliminada correctamente"}

# ENDPOINTS PARA PUBLICACIONES
@router.post("/publicaciones/")
async def crear_publicacion(
    id_usuario: int = Form(...),
    contenido: str = Form(...),
    foto_publicacion: Optional[UploadFile] = File(None)
):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    foto_filename = None
    if foto_publicacion:
        foto_filename = await save_image(foto_publicacion, POST_IMAGES_DIR)
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Publicaciones 
        (id_usuario, contenido, fecha_publicacion, foto_publicacion) 
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (
        id_usuario, contenido, 
        datetime.datetime.now(), foto_filename
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Publicación creada correctamente"}

@router.get("/publicaciones/{id_publicacion}")
def obtener_publicacion(id_publicacion: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Publicaciones WHERE id_publicacion = %s"
    cursor.execute(query, (id_publicacion,))
    publicacion = cursor.fetchone()
    cursor.close()
    conn.close()

    if not publicacion:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")

    return publicacion

@router.put("/publicaciones/{id_publicacion}")
async def actualizar_publicacion(
    id_publicacion: int,
    contenido: Optional[str] = Form(None),
    foto_publicacion: Optional[UploadFile] = File(None)
):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Publicaciones WHERE id_publicacion = %s", (id_publicacion,))
    publicacion = cursor.fetchone()
    
    if not publicacion:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    
    update_fields = {}
    if contenido: update_fields['contenido'] = contenido
    
    if foto_publicacion:
        foto_filename = await save_image(foto_publicacion, POST_IMAGES_DIR)
        update_fields['foto_publicacion'] = foto_filename
    
    if update_fields:
        set_clause = ", ".join([f"{k} = %s" for k in update_fields])
        values = list(update_fields.values())
        values.append(id_publicacion)
        
        query = f"UPDATE Publicaciones SET {set_clause} WHERE id_publicacion = %s"
        cursor.execute(query, values)
        conn.commit()
    
    return {"mensaje": "Publicación actualizada correctamente"}

@router.delete("/publicaciones/{id_publicacion}")
def eliminar_publicacion(id_publicacion: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Publicaciones WHERE id_publicacion = %s"
    cursor.execute(query, (id_publicacion,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Publicación eliminada correctamente"}

# ENDPOINTS PARA COMENTARIOS
@router.post("/comentarios/")
def crear_comentario(comentario: Comentario):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Comentarios 
        (id_publicacion, id_usuario, contenido, fecha_comentario) 
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (
        comentario.id_publicacion, 
        comentario.id_usuario, 
        comentario.contenido, 
        datetime.datetime.now()
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Comentario añadido correctamente"}

@router.delete("/comentarios/{id_comentario}")
def eliminar_comentario(id_comentario: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Comentarios WHERE id_comentario = %s"
    cursor.execute(query, (id_comentario,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Comentario eliminado correctamente"}

# ENDPOINTS PARA MENSAJES
@router.post("/mensajes/")
def enviar_mensaje(mensaje: Mensaje):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Mensajes 
        (id_emisor, id_receptor, contenido, fecha_envio) 
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (
        mensaje.id_emisor, 
        mensaje.id_receptor, 
        mensaje.contenido, 
        datetime.datetime.now()
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Mensaje enviado correctamente"}

@router.get("/mensajes/{id_receptor}")
def obtener_mensajes(id_receptor: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Mensajes WHERE id_receptor = %s"
    cursor.execute(query, (id_receptor,))
    mensajes = cursor.fetchall()
    cursor.close()
    conn.close()

    return mensajes

@router.delete("/mensajes/{id_mensaje}")
def eliminar_mensaje(id_mensaje: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Mensajes WHERE id_mensaje = %s"
    cursor.execute(query, (id_mensaje,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Mensaje eliminado correctamente"}

# ENDPOINTS PARA ADOPCIONES
@router.post("/adopciones/")
def crear_adopcion(adopcion: Adopcion):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Adopciones 
        (id_mascota, id_usuario_adoptante, fecha_adopcion) 
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (
        adopcion.id_mascota, 
        adopcion.id_usuario_adoptante, 
        adopcion.fecha_adopcion
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Adopción registrada correctamente"}

@router.get("/adopciones/{id_mascota}")
def obtener_adopciones_mascota(id_mascota: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Adopciones WHERE id_mascota = %s"
    cursor.execute(query, (id_mascota,))
    adopciones = cursor.fetchall()
    cursor.close()
    conn.close()

    return adopciones

@router.delete("/adopciones/{id_adopcion}")
def eliminar_adopcion(id_adopcion: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Adopciones WHERE id_adopcion = %s"
    cursor.execute(query, (id_adopcion,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Adopción eliminada correctamente"}

# ENDPOINTS PARA ME GUSTA
@router.post("/megusta/")
def crear_megusta(megusta: MeGusta):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO MeGusta 
        (id_publicacion, id_usuario, fecha) 
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (
        megusta.id_publicacion, 
        megusta.id_usuario, 
        datetime.datetime.now()
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Me gusta registrado correctamente"}

@router.get("/megusta/{id_publicacion}")
def obtener_megusta_publicacion(id_publicacion: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM MeGusta WHERE id_publicacion = %s"
    cursor.execute(query, (id_publicacion,))
    megustas = cursor.fetchall()
    cursor.close()
    conn.close()

    return megustas

@router.delete("/megusta/{id_megusta}")
def eliminar_megusta(id_megusta: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM MeGusta WHERE id_megusta = %s"
    cursor.execute(query, (id_megusta,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Me gusta eliminado correctamente"}

# ENDPOINTS PARA CATEGORIAS
@router.post("/categorias/")
def crear_categoria(categoria: Categoria):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "INSERT INTO Categorias (nombre) VALUES (%s)"
    cursor.execute(query, (categoria.nombre,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Categoría creada correctamente"}

@router.get("/categorias/")
def obtener_categorias():
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Categorias"
    cursor.execute(query)
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()

    return categorias

@router.delete("/categorias/{id_categoria}")
def eliminar_categoria(id_categoria: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Categorias WHERE id_categoria = %s"
    cursor.execute(query, (id_categoria,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Categoría eliminada correctamente"}

# ENDPOINTS PARA PRODUCTOS
@router.post("/productos/")
def crear_producto(producto: Producto):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        INSERT INTO Productos 
        (nombre, descripcion, precio, imagen, id_usuario_empresa, id_categoria, link_externo) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        producto.nombre,
        producto.descripcion,
        producto.precio,
        producto.imagen,
        producto.id_usuario_empresa,
        producto.id_categoria,
        producto.link_externo
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Producto creado correctamente"}

@router.get("/productos/{id_categoria}")
def obtener_productos_por_categoria(id_categoria: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Productos WHERE id_categoria = %s"
    cursor.execute(query, (id_categoria,))
    productos = cursor.fetchall()
    cursor.close()
    conn.close()

    return productos

@router.put("/productos/{id_producto}")
def actualizar_producto(id_producto: int, producto: Producto):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = """
        UPDATE Productos 
        SET nombre = %s, descripcion = %s, precio = %s, 
            imagen = %s, id_categoria = %s, link_externo = %s 
        WHERE id_producto = %s
    """
    cursor.execute(query, (
        producto.nombre, 
        producto.descripcion, 
        producto.precio,
        producto.imagen, 
        producto.id_categoria, 
        producto.link_externo, 
        id_producto
    ))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Producto actualizado correctamente"}

@router.delete("/productos/{id_producto}")
def eliminar_producto(id_producto: int):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor()
    query = "DELETE FROM Productos WHERE id_producto = %s"
    cursor.execute(query, (id_producto,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Producto eliminado correctamente"}

# ENDPOINT PARA INICIAR SESIÓN
@router.get("/login/")
def login(correo: str, contraseña: str):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD")
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM Usuarios WHERE email = %s AND contraseña = %s"
    cursor.execute(query, (correo, contraseña))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if not usuario:
        raise HTTPException(status_code=404, detail="Correo o contraseña incorrectos")
    
    return {"mensaje": "Inicio de sesión exitoso", "usuario": usuario}