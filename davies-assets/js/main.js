/**
 * Go Top
 * Infinite Slide
 * Update Clock
 * Cursor Trail
 * Counter
 * Scroll Link
 * Setting Color
 * Open Menu
 * Click Active
 */

(function ($) {
    "use strict";

    /* Go Top
    -------------------------------------------------------------------------*/
    var goTop = function () {
        var $goTop = $("#goTop");
        var $borderProgress = $(".border-progress");
        var $footer = $(".tf-footer");

        $(window).on("scroll", function () {
            var scrollTop = $(window).scrollTop();
            var docHeight = $(document).height() - $(window).height();
            var scrollPercent = (scrollTop / docHeight) * 100;
            var progressAngle = (scrollPercent / 100) * 360;

            $borderProgress.css("--progress-angle", progressAngle + "deg");

            var windowBottom = scrollTop + $(window).height();
            var hasFooter = $footer.length > 0;
            var footerOffset = hasFooter ? $footer.offset().top : Infinity;

            if (scrollTop > 100 && windowBottom < footerOffset) {
                $goTop.addClass("show");
            } else {
                $goTop.removeClass("show");
            }
        });

        $goTop.on("click", function () {
            $("html, body").animate({ scrollTop: 0 }, 100);
        });
    };
    /* Infinite Slide 
    -------------------------------------------------------------------------*/
    var infiniteSlide = function () {
        if ($(".infiniteSlide").length > 0) {
            $(".infiniteSlide").each(function () {
                var $this = $(this);
                var style = $this.data("style") || "left";
                var clone = $this.data("clone") || 2;
                var speed = $this.data("speed") || 50;
                $this.infiniteslide({
                    speed: speed,
                    direction: style,
                    clone: clone,
                    pauseonhover: false,
                });
            });
        }
    };
    /* Update Clock
    -------------------------------------------------------------------------*/
    var updateClock = () => {
        function startClocks(selector = ".clock") {
            function updateClock() {
                const now = new Date();
                const timeString = now.toLocaleTimeString("en-GB");
                document.querySelectorAll(selector).forEach((el) => {
                    el.textContent = timeString;
                });
            }
            updateClock();
            setInterval(updateClock, 1000);
        }

        startClocks(".clock");
    };
    /* Cursor Trail (Disabled)
    -------------------------------------------------------------------------*/
    var cursorTrail = () => {
        // Cursor trail line disabled per user request
    };
    /* Counter Odo
    -------------------------------------------------------------------------*/
    var counterOdo = () => {
        function isElementInViewport($el) {
            var top = $el.offset().top;
            var bottom = top + $el.outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();
            return bottom > viewportTop && top < viewportBottom;
        }
        if ($(".counter-scroll").length > 0) {
            $(window).on("scroll", function () {
                $(".wg-counter").each(function () {
                    var $counter = $(this);
                    if (isElementInViewport($counter) && !$counter.hasClass("counted")) {
                        $counter.addClass("counted");
                        var targetNumber = $counter.find(".odometer").data("number");
                        setTimeout(function () {
                            $counter.find(".odometer").text(targetNumber);
                        }, 0);
                    }
                });
            });
        }
    };
    /* Setting Color
    -------------------------------------------------------------------------*/
    const settingColor = () => {
        if (!$(".settings-color").length) return;

        const COLOR_KEY = "selectedColorIndex";

        const savedIndex = localStorage.getItem(COLOR_KEY);

        if (savedIndex !== null) {
            setColor(savedIndex);
            setActiveItem(savedIndex - 1);
        }

        $(".choose-item").on("click", function () {
            const index = $(this).index();
            setColor(index + 1);
            setActiveItem(index);
            localStorage.setItem(COLOR_KEY, index + 1);
        });

        function setColor(index) {
            $("body").attr("data-color-primary", "color-primary-" + index);
        }

        function setActiveItem(index) {
            $(".choose-item").removeClass("active").eq(index).addClass("active");
        }
    };
    /* Open Menu
    -------------------------------------------------------------------------*/
    var openMbMenu = () => {
        $(".open-mb-menu").on("click", function () {
            $(".offcanvas-menu").addClass("show");
            $("body").toggleClass("overflow-hidden");
        });

        $(".close-mb-menu").on("click", function () {
            $(".offcanvas-menu").removeClass("show");
            $("body").toggleClass("overflow-hidden");
        });
    };
    /* Click Active
    -------------------------------------------------------------------------*/
    var clickActive = () => {
        $(".btn-active").on("mouseenter", function () {
            var $btn = $(this);
            if ($btn.hasClass("active")) {
            } else {
                $(".main-action-active .btn-active").removeClass("active");
                $btn.addClass("active");
            }
        });
    };

    // Dom Ready
    $(function () {
        infiniteSlide();
        updateClock();
        // cursorTrail(); // Disabled per user request
        goTop();
        // settingColor();
        counterOdo();
        openMbMenu();
        clickActive();
    });
})(jQuery);
