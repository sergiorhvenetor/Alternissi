function changeMainImage(imageUrl, thumbnailElement) {
    document.getElementById('mainProductImage').src = imageUrl;

    const thumbnails = document.querySelectorAll('.product-detail__image-gallery .thumbnail-images img');
    thumbnails.forEach(thumb => thumb.classList.remove('active-thumbnail'));
    if (thumbnailElement) {
        thumbnailElement.classList.add('active-thumbnail');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Activar la primera miniatura por defecto
    const firstThumbnail = document.querySelector('.product-detail__image-gallery .thumbnail-images img');
    if (firstThumbnail) {
        firstThumbnail.classList.add('active-thumbnail');
        // No es necesario llamar a changeMainImage aquí si el src de la imagen principal ya es el de la primera miniatura
    }

    // Inicializar Tabs de Bootstrap
    var triggerTabList = [].slice.call(document.querySelectorAll('#productTab button[data-bs-toggle="tab"]'))
    triggerTabList.forEach(function (triggerEl) {
      var tabTrigger = new bootstrap.Tab(triggerEl)
      triggerEl.addEventListener('click', function (event) {
        event.preventDefault()
        tabTrigger.show()
      })
    })
});
