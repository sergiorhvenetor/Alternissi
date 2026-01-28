document.addEventListener('DOMContentLoaded', function () {
    const cartCountElement = document.getElementById('cart-count');

    // Función para actualizar el contador del carrito
    function updateCartCount(newCount) {
        if (cartCountElement) {
            cartCountElement.textContent = newCount;
        }
    }

    // Función genérica para manejar formularios AJAX del carrito
    async function handleCartFormSubmit(form, onSuccess) {
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    // Django espera CSRF token para POST
                    'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            if (!response.ok) {
                console.error('Error en la respuesta del servidor:', response.status);
                // Mostrar un mensaje de error genérico al usuario si es necesario
                // alert('Ocurrió un error. Por favor, intenta de nuevo.');
                return;
            }

            const data = await response.json();

            if (data.success) {
                if (data.cart_total_items_display !== undefined) {
                    updateCartCount(data.cart_total_items_display);
                }
                if (onSuccess && typeof onSuccess === 'function') {
                    onSuccess(data); // Pasar todos los datos para mayor flexibilidad
                }
                // Opcional: mostrar mensaje de éxito con data.message
                // if (data.message) {
                //     alert(data.message);
                // }
            } else {
                console.error('Error al procesar la solicitud:', data.message);
                // Mostrar mensaje de error específico si está disponible
                // if (data.message) {
                //    alert(data.message);
                // }
            }
        } catch (error) {
            console.error('Error en la solicitud AJAX:', error);
            // alert('Ocurrió un error de red. Por favor, intenta de nuevo.');
        }
    }

    // Interceptar envíos de formularios "Agregar al Carrito"
    // Asumimos que los formularios para agregar al carrito tienen una clase 'add-to-cart-form'
    // o un identificador específico. Ajustar el selector según sea necesario.
    document.querySelectorAll('form.add-to-cart-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            handleCartFormSubmit(this, function(data) {
                // Lógica adicional después de agregar al carrito, si es necesaria
                // Por ejemplo, mostrar una notificación
                console.log('Producto agregado:', data);
                if (data.message) {
                  // Podrías usar una librería de notificaciones más elegante aquí
                  alert(data.message);
                }
            });
        });
    });

    // Interceptar clics en botones "Eliminar del Carrito" en la página del carrito
    // Asumimos que estos botones están dentro de formularios con clase 'remove-from-cart-form'
    // y que el item_id está en la URL de acción del formulario.
    // Esto es para la página del carrito.
    document.querySelectorAll('form.remove-from-cart-form').forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            handleCartFormSubmit(this, function(data) {
                if (data.success && data.removed !== undefined) { // Check for removed specifically
                    // Eliminar la fila del item del carrito de la tabla
                    const itemRow = form.closest('tr'); // o el contenedor del item
                    if (itemRow && data.removed) { // Only remove if data.removed is true
                        itemRow.remove();
                    }
                    // Actualizar totales en la página del carrito si es necesario
                    if (document.getElementById('cart-subtotal') && data.cart_subtotal_display !== undefined) {
                        document.getElementById('cart-subtotal').textContent = '$' + data.cart_subtotal_display;
                    }
                    if (document.getElementById('cart-total') && data.cart_total_display !== undefined) {
                        document.getElementById('cart-total').textContent = '$' + data.cart_total_display;
                    }
                     if (document.getElementById('cart-discount') && data.cart_discount_amount_display !== undefined) {
                        document.getElementById('cart-discount').textContent = '-$' + data.cart_discount_amount_display;
                        const discountRow = document.getElementById('cart-discount-row');
                        if (discountRow) {
                            if (parseFloat(data.cart_discount_amount_display) > 0) {
                                discountRow.style.setProperty('display', 'flex', 'important');
                            } else {
                                discountRow.style.setProperty('display', 'none', 'important');
                            }
                        }
                    }
                    // Podrías usar una librería de notificaciones más elegante aquí
                    if (data.message) {
                        alert(data.message);
                    }

                    // Si el carrito queda vacío, mostrar un mensaje
                    if (data.cart_total_items_display === 0) {
                        const cartTableContainer = document.querySelector('.cart-table-container'); // Ajusta el selector al contenedor de la tabla
                        if (cartTableContainer) {
                            cartTableContainer.innerHTML = '<p>Tu carrito está vacío.</p>';
                        }
                    }
                } else if (data.success && data.message) { // Handle cases where item might not be 'removed' but action was success (e.g. error during removal shown as success:false)
                   // alert(data.message); // Alert if there's a message but not necessarily removed
                }
            });
        });
    });

    // Interceptar cambios en la cantidad de items en la página del carrito
    // Asumimos que los inputs de cantidad tienen clase 'cart-item-quantity-input'
    // y que el item_id está en un atributo data o en la URL del formulario asociado.
    // Esto es para la página del carrito.
    document.querySelectorAll('input.cart-item-quantity-input').forEach(input => {
        input.addEventListener('change', function () {
            const form = this.closest('form.update-cart-item-form'); // Asumimos que el input está en un form
            if (form) {
                 handleCartFormSubmit(form, function(data) {
                    if (data.success) {
                        // Actualizar subtotal del item
                        const itemRow = input.closest('tr'); // o el contenedor del item
                        if (itemRow) {
                            const itemSubtotalElement = itemRow.querySelector('.item-subtotal');
                            if (itemSubtotalElement && data.item_subtotal !== undefined) {
                                itemSubtotalElement.textContent = '$' + data.item_subtotal;
                            }
                        }
                        // Actualizar totales en la página del carrito
                        if (document.getElementById('cart-subtotal') && data.cart_subtotal_display !== undefined) {
                            document.getElementById('cart-subtotal').textContent = '$' + data.cart_subtotal_display;
                        }
                        if (document.getElementById('cart-total') && data.cart_total_display !== undefined) {
                            document.getElementById('cart-total').textContent = '$' + data.cart_total_display;
                        }
                        if (document.getElementById('cart-discount') && data.cart_discount_amount_display !== undefined) {
                            document.getElementById('cart-discount').textContent = '-$' + data.cart_discount_amount_display;
                            const discountRow = document.getElementById('cart-discount-row');
                            if (discountRow) {
                                if (parseFloat(data.cart_discount_amount_display) > 0) {
                                    discountRow.style.setProperty('display', 'flex', 'important');
                                } else {
                                    discountRow.style.setProperty('display', 'none', 'important');
                                }
                            }
                        }
                        // Si el item fue removido (cantidad 0)
                        if (data.removed && itemRow) {
                            itemRow.remove();
                             if (data.message) alert(data.message);
                        } else if (data.message) {
                            // alert(data.message); // Opcional: notificar al usuario si no fue removido pero hubo un mensaje
                        }

                        if (data.cart_total_items_display === 0) {
                            const cartTableContainer = document.querySelector('.cart-table-container'); // Ajusta el selector
                            if (cartTableContainer) {
                                cartTableContainer.innerHTML = '<p>Tu carrito está vacío.</p>';
                            }
                        }
                    }
                });
            }
        });
    });

    // Evitar que los formularios de actualización se envíen normalmente al presionar Enter
    document.querySelectorAll('form.update-cart-item-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            // El evento 'change' del input ya debería haber disparado la actualización,
            // pero podemos llamarlo aquí explícitamente si queremos asegurar.
        });
    });

    // Inicializar el contador del carrito al cargar la página si ya hay un valor.
    // Esto es más para asegurar que si el valor está en el HTML, se muestre.
    // El valor inicial correcto debe venir del context processor.
    // Si el `cart_processor` funciona bien, `cartCountElement.textContent` ya tendrá el valor correcto.
});
