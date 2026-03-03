// Main JavaScript for GERALDINE'S STYLE HAVEN

// Initialize on document ready
$(document).ready(function() {
    initShop();
});

function initShop() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Smooth scrolling for anchor links
    $('a[href*="#"]').not('[href="#"]').not('[href="#0"]').click(function(event) {
        if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') && location.hostname == this.hostname) {
            var target = $(this.hash);
            target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
            if (target.length) {
                event.preventDefault();
                $('html, body').animate({
                    scrollTop: target.offset().top - 76
                }, 1000);
            }
        }
    });

    // Add to cart animation
    $('.add-to-cart').click(function(e) {
        e.preventDefault();
        var btn = $(this);
        btn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...');

        setTimeout(function() {
            btn.html('<i class="fas fa-check"></i> Added!');
            setTimeout(function() {
                btn.html('<i class="fas fa-shopping-bag"></i> Add to Cart');
            }, 2000);
        }, 1000);
    });

    // Product quick view
    $('.quick-view').click(function(e) {
        e.preventDefault();
        var productId = $(this).data('product-id');
        // Implement quick view modal
        loadQuickView(productId);
    });

    // Newsletter subscription
    $('#newsletter-form').submit(function(e) {
        e.preventDefault();
        var email = $('#newsletter-email').val();

        if (isValidEmail(email)) {
            $.ajax({
                url: '/subscribe',
                method: 'POST',
                data: { email: email },
                success: function(response) {
                    showNotification('Successfully subscribed!', 'success');
                    $('#newsletter-email').val('');
                },
                error: function() {
                    showNotification('An error occurred. Please try again.', 'error');
                }
            });
        } else {
            showNotification('Please enter a valid email address.', 'error');
        }
    });

    // Product filters
    $('#apply-filters').click(function() {
        var filters = getFilters();
        loadProducts(filters);
    });

    // Price range filter
    $('#priceRange').on('input', function() {
        var value = $(this).val();
        $('#priceValue').text('$' + value);
    });

    // Size selection
    $('.size-option').click(function() {
        $('.size-option').removeClass('active');
        $(this).addClass('active');
    });

    // Color selection
    $('.color-option').click(function() {
        $('.color-option').removeClass('active');
        $(this).addClass('active');
    });

    // Image gallery
    $('.thumbnail-img').click(function() {
        var newSrc = $(this).attr('src');
        $('#main-product-image').attr('src', newSrc);
        $('.thumbnail-img').removeClass('active');
        $(this).addClass('active');
    });
}

// Helper Functions
function isValidEmail(email) {
    var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
}

function showNotification(message, type) {
    // Create notification element
    var notification = $('<div class="alert alert-' + (type === 'success' ? 'success' : 'danger') + ' alert-dismissible fade show position-fixed top-0 end-0 m-3" role="alert">' +
        message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
        '</div>');

    $('body').append(notification);

    // Auto dismiss after 3 seconds
    setTimeout(function() {
        notification.alert('close');
    }, 3000);
}

function getFilters() {
    var filters = {};

    // Get selected categories
    filters.category = $('#category-select').val();

    // Get price range
    filters.minPrice = $('#min-price').val();
    filters.maxPrice = $('#max-price').val();

    // Get selected sizes
    filters.sizes = [];
    $('.size-option.active').each(function() {
        filters.sizes.push($(this).data('size'));
    });

    // Get selected colors
    filters.colors = [];
    $('.color-option.active').each(function() {
        filters.colors.push($(this).data('color'));
    });

    return filters;
}

function loadProducts(filters) {
    // Show loading spinner
    $('#products-grid').html('<div class="text-center py-5"><div class="spinner"></div></div>');

    // Simulate AJAX call
    setTimeout(function() {
        // In real implementation, you would make an AJAX call here
        console.log('Loading products with filters:', filters);
        // location.reload(); // Simple reload for demo
    }, 1000);
}

function loadQuickView(productId) {
    // Create modal
    var modal = `
        <div class="modal fade" id="quickViewModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Quick View</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center">
                            <div class="spinner"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    $('body').append(modal);

    // Load product data
    $.ajax({
        url: '/product/' + productId + '/quick-view',
        method: 'GET',
        success: function(data) {
            $('#quickViewModal .modal-body').html(data);
        },
        error: function() {
            $('#quickViewModal .modal-body').html('<p class="text-center text-danger">Error loading product.</p>');
        }
    });

    // Show modal
    var quickViewModal = new bootstrap.Modal(document.getElementById('quickViewModal'));
    quickViewModal.show();

    // Clean up on hide
    $('#quickViewModal').on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

// Lazy loading images
document.addEventListener("DOMContentLoaded", function() {
    var lazyImages = [].slice.call(document.querySelectorAll("img.lazy"));

    if ("IntersectionObserver" in window) {
        let lazyImageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    let lazyImage = entry.target;
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.remove("lazy");
                    lazyImageObserver.unobserve(lazyImage);
                }
            });
        });

        lazyImages.forEach(function(lazyImage) {
            lazyImageObserver.observe(lazyImage);
        });
    }
});

// Sticky header on scroll
window.addEventListener('scroll', function() {
    var header = document.querySelector('.navbar');
    if (window.scrollY > 100) {
        header.classList.add('shadow');
    } else {
        header.classList.remove('shadow');
    }
});

// Back to top button
$(window).scroll(function() {
    if ($(this).scrollTop() > 300) {
        $('.back-to-top').fadeIn('slow');
    } else {
        $('.back-to-top').fadeOut('slow');
    }
});

$('.back-to-top').click(function() {
    $('html, body').animate({
        scrollTop: 0
    }, 800);
    return false;
});