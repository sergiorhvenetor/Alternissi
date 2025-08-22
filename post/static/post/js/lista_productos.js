document.addEventListener('DOMContentLoaded', function() {
    const sortForm = document.getElementById('sortForm');
    if (sortForm) {
        const selectElement = sortForm.querySelector('select[name="orden"]');

        // Conservar el slug de la categoría/marca en la URL base del formulario
        // si la vista actual es una de categoría o marca específica.
        // Esto asegura que al cambiar el orden, se mantenga el filtro de categoría/marca.
        const pathParts = window.location.pathname.split('/');
        let formAction = "{% url 'tienda:lista_productos' %}"; // URL base

        if (pathParts.includes('categoria') && pathParts.length > pathParts.indexOf('categoria') + 1) {
            const categoriaSlug = pathParts[pathParts.indexOf('categoria') + 1];
            if (categoriaSlug) {
                formAction = "{% url 'tienda:productos_por_categoria' 'SLUG_PLACEHOLDER' %}".replace('SLUG_PLACEHOLDER', categoriaSlug);
                // Añadir input hidden para categoria_slug si no está ya (para el GET)
                if (!sortForm.querySelector('input[name="categoria_slug"]')) {
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'categoria_slug'; // O el nombre que espera la vista
                    hiddenInput.value = categoriaSlug;
                    sortForm.appendChild(hiddenInput);
                }
            }
        } else if (pathParts.includes('marca') && pathParts.length > pathParts.indexOf('marca') + 1) {
            const marcaSlug = pathParts[pathParts.indexOf('marca') + 1];
            if (marcaSlug) {
                formAction = "{% url 'tienda:productos_por_marca' 'SLUG_PLACEHOLDER' %}".replace('SLUG_PLACEHOLDER', marcaSlug);
                 if (!sortForm.querySelector('input[name="marca_slug"]')) {
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'marca_slug'; // O el nombre que espera la vista
                    hiddenInput.value = marcaSlug;
                    sortForm.appendChild(hiddenInput);
                }
            }
        }
        sortForm.action = formAction;

        // Script para manejar el cambio de orden (onchange ya lo hace, esto es por si se quita)
        // if (selectElement) {
        //     selectElement.addEventListener('change', function() {
        //         sortForm.submit();
        //     });
        // }
    }

    // Actualizar los href de los filtros para que mantengan 'q' y 'orden'
    const filterLinks = document.querySelectorAll('.filters .filter-list a');
    const currentParams = new URLSearchParams(window.location.search);
    const currentSortOrder = currentParams.get('orden');
    const currentSearchQuery = currentParams.get('q');

    filterLinks.forEach(link => {
        const url = new URL(link.href); // El href ya debería ser la URL base correcta para el filtro

        // Limpiar q y orden del enlace base para no duplicar si ya están en currentParams
        url.searchParams.delete('q');
        url.searchParams.delete('orden');

        if (currentSearchQuery) {
            url.searchParams.set('q', currentSearchQuery);
        }
        if (currentSortOrder) {
            url.searchParams.set('orden', currentSortOrder);
        }
        link.href = url.toString();
    });
});
