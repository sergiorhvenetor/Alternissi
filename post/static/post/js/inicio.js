document.addEventListener('DOMContentLoaded', function () {
    const carousels = document.querySelectorAll('.carousel-wrapper');

    carousels.forEach(wrapper => {
        const carouselId = wrapper.querySelector('.product-carousel')?.id;
        if (!carouselId) return;

        const carousel = document.getElementById(carouselId);
        const prevBtn = wrapper.querySelector('.prev-btn[data-carousel="' + carouselId + '"]');
        const nextBtn = wrapper.querySelector('.next-btn[data-carousel="' + carouselId + '"]');

        // Dinámicamente obtener el ancho de la tarjeta, incluyendo el gap
        let cardWidth = 0;
        const firstCard = carousel.querySelector('.product-card');
        if (firstCard) {
            const cardStyle = window.getComputedStyle(firstCard);
            const cardMarginRight = parseFloat(cardStyle.marginRight) || 0; // O el gap si se usa así
            const carouselStyle = window.getComputedStyle(carousel);
            const carouselGap = parseFloat(carouselStyle.gap) || 20; // Fallback al gap definido en CSS
            cardWidth = firstCard.offsetWidth + Math.max(cardMarginRight, carouselGap) ;
        }


        function updateButtons() {
            if (!carousel || !prevBtn || !nextBtn) return;
            const scrollLeft = carousel.scrollLeft;
            const scrollWidth = carousel.scrollWidth;
            const clientWidth = carousel.clientWidth;

            prevBtn.disabled = scrollLeft <= 0;
            // Pequeña tolerancia para el final del scroll
            nextBtn.disabled = scrollLeft >= (scrollWidth - clientWidth - 5);
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (carousel && cardWidth > 0) {
                    carousel.scrollBy({ left: -cardWidth, behavior: 'smooth' });
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (carousel && cardWidth > 0) {
                    carousel.scrollBy({ left: cardWidth, behavior: 'smooth' });
                }
            });
        }

        if (carousel) {
            carousel.addEventListener('scroll', updateButtons);
            // Observador para cuando las imágenes carguen y cambie el tamaño del carrusel
            const resizeObserver = new ResizeObserver(() => {
                // Recalcular cardWidth si es necesario (especialmente si las imágenes tardan en cargar)
                if (firstCard) {
                    const cardStyle = window.getComputedStyle(firstCard);
                    const cardMarginRight = parseFloat(cardStyle.marginRight) || 0;
                    const carouselStyle = window.getComputedStyle(carousel);
                    const carouselGap = parseFloat(carouselStyle.gap) || 20;
                    cardWidth = firstCard.offsetWidth + Math.max(cardMarginRight, carouselGap) ;
                }
                updateButtons();
            });
            resizeObserver.observe(carousel);

            // También llamar a updateButtons al cargar y al cambiar tamaño de ventana (responsive)
            // Dar un pequeño tiempo para que las imágenes puedan cargar y se calcule bien el cardWidth
            setTimeout(updateButtons, 300);
            window.addEventListener('resize', () => {
                 if (firstCard) { // Recalcular en resize
                    const cardStyle = window.getComputedStyle(firstCard);
                    const cardMarginRight = parseFloat(cardStyle.marginRight) || 0;
                    const carouselStyle = window.getComputedStyle(carousel);
                    const carouselGap = parseFloat(carouselStyle.gap) || 20;
                    cardWidth = firstCard.offsetWidth + Math.max(cardMarginRight, carouselGap) ;
                }
                updateButtons();
            });
        }
    });
});
