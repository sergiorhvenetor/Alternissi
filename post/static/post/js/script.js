function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
    const botonesListaDeseos = document.querySelectorAll('.boton-lista-deseos');

    botonesListaDeseos.forEach(boton => {
        const productoId = boton.dataset.productoId;
        let iconoCorazon = boton.querySelector('.icono-corazon');

        // En inicio.html y otras tarjetas, el botón en sí es el ícono si no hay un span .icono-corazon
        // En detalle_producto.html, .icono-corazon es un span dentro del botón.
        const esIconoDirecto = !iconoCorazon;
        if (esIconoDirecto) {
            iconoCorazon = boton;
        }

        const textoBoton = boton.querySelector('.texto-lista-deseos'); // Solo existe en detalle_producto.html
        const mensajeListaDeseos = document.querySelector(`.mensaje-lista-deseos[data-producto-id="${productoId}"]`);

        // 1. Obtener estado inicial al cargar la página
        fetch(`/deseos/estado/${productoId}/`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest' // Importante para que Django sepa que es AJAX
            }
        })
        .then(response => {
            if (!response.ok) {
                // Intentar leer el cuerpo del error si es JSON
                return response.json().then(errData => {
                    throw new Error(errData.error || `HTTP error! status: ${response.status}`);
                }).catch(() => {
                    // Si el cuerpo del error no es JSON o está vacío
                    throw new Error(`HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(`Error al obtener estado de lista de deseos para producto ${productoId}: ${data.error}`);
                if (mensajeListaDeseos) {
                    mensajeListaDeseos.textContent = `Error estado: ${data.error}`;
                    mensajeListaDeseos.style.display = 'inline';
                    mensajeListaDeseos.style.color = 'red';
                    setTimeout(() => {
                        mensajeListaDeseos.style.display = 'none';
                        mensajeListaDeseos.textContent = '';
                    }, 3000);
                }
                return;
            }
            iconoCorazon.innerHTML = data.esta_en_lista ? '❤️' : '♡';
            if (textoBoton) {
                textoBoton.textContent = data.esta_en_lista ? 'Quitar de Lista de Deseos' : 'Añadir a Lista de Deseos';
            }
        })
        .catch(error => {
            console.error(`Error en fetch (estado lista de deseos) para producto ${productoId}:`, error);
            if (mensajeListaDeseos) {
                mensajeListaDeseos.textContent = error.message || 'Error de conexión al verificar estado.';
                mensajeListaDeseos.style.display = 'inline';
                mensajeListaDeseos.style.color = 'red';
                 setTimeout(() => {
                        mensajeListaDeseos.style.display = 'none';
                        mensajeListaDeseos.textContent = '';
                    }, 3000);
            }
        });

        // 2. Evento click para agregar/quitar
        boton.addEventListener('click', function(event) {
            event.preventDefault();

            fetch(`/deseos/agregar/${productoId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest' // Importante
                },
                // body: JSON.stringify({}) // Cuerpo vacío es suficiente ya que el ID está en la URL
            })
            .then(response => {
                 if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.error || `HTTP error! status: ${response.status}`);
                    }).catch(() => {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    console.error(`Error al agregar/quitar de lista de deseos para producto ${productoId}: ${data.error}`);
                    if (mensajeListaDeseos) {
                        mensajeListaDeseos.textContent = data.error;
                        mensajeListaDeseos.style.color = 'red';
                    }
                } else {
                    iconoCorazon.innerHTML = data.agregado ? '❤️' : '♡';
                    if (textoBoton) {
                        textoBoton.textContent = data.agregado ? 'Quitar de Lista de Deseos' : 'Añadir a Lista de Deseos';
                    }
                    if (mensajeListaDeseos) {
                        mensajeListaDeseos.textContent = data.mensaje;
                        // Cambiar color según éxito/acción
                        if (data.agregado === true) { // Producto añadido
                            mensajeListaDeseos.style.color = 'green';
                        } else if (data.agregado === false) { // Producto eliminado
                            mensajeListaDeseos.style.color = 'orange';
                        } else { // neutral o error no capturado antes
                             mensajeListaDeseos.style.color = 'black';
                        }
                    }
                }

                if (mensajeListaDeseos) {
                    mensajeListaDeseos.style.display = 'inline';
                    setTimeout(() => {
                        mensajeListaDeseos.style.display = 'none';
                        mensajeListaDeseos.textContent = '';
                    }, 4000);
                }
            })
            .catch(error => {
                console.error(`Error en fetch (agregar/quitar lista de deseos) para producto ${productoId}:`, error);
                if (mensajeListaDeseos) {
                    mensajeListaDeseos.textContent = error.message || 'Error de conexión.';
                    mensajeListaDeseos.style.color = 'red';
                    mensajeListaDeseos.style.display = 'inline';
                    setTimeout(() => {
                        mensajeListaDeseos.style.display = 'none';
                        mensajeListaDeseos.textContent = '';
                    }, 4000);
                }
            });
        });
    });
});
