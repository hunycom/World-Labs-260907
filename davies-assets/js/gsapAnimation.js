(function ($) {
    "use strict";
    // DOM Ready

    var changetext = function () {
        if ($(".text-color-change").length) {
            $(".text-color-change").each(function () {
                const $el = $(this)[0];

                $el.wordSplit?.revert();
                $el.charSplit?.revert();

                $el.wordSplit = new SplitText($el, { type: "words", wordsClass: "word-wrapper" });
                $el.charSplit = new SplitText($el.wordSplit.words, { type: "chars", charsClass: "char-wrapper" });

                gsap.set($el.charSplit.chars, { color: "#FFFFFF52" });

                gsap.to($el.charSplit.chars, {
                    color: "#ffffff",
                    stagger: { each: 0.03, from: "start" },
                    ease: "power2.out",
                    scrollTrigger: {
                        trigger: $el,
                        start: "top 70%",
                        end: "bottom 20%",
                        scrub: true,
                        toggleActions: "play none none reverse",
                    },
                });
            });
        }
    };

    var gsapA2 = () => {
        if ($(".gsap-anime-2").length) {
            const cards = document.querySelectorAll(".flip-image");

            function animate() {
                const isMobile = window.innerWidth < 767;
                const cardW = isMobile ? 150 : 325;
                const cardH = isMobile ? 150 : 325;

                const parent = cards[0].parentElement;
                parent.style.position = "relative";
                const centerX = parent.clientWidth / 2 - cardW / 2;
                const centerY = parent.clientHeight / 2 - cardH / 2;

                cards.forEach((card, i) => {
                    card.style.position = "absolute";
                    card.style.zIndex = i + 1;
                });

                const tl = gsap.timeline({
                    defaults: { ease: "power3.out" },
                    scrollTrigger: {
                        trigger: ".gsap-anime-2",
                        start: "top 80%",
                        toggleActions: "play none none reverse",
                    },
                });

                tl.to(cards, {
                    x: centerX,
                    y: centerY,
                    opacity: 1,
                    duration: 1,
                    stagger: 0.1,
                }).to(cards, {
                    x: (i) => {
                        if (i === 0) return centerX - (isMobile ? 180 : 400);
                        if (i === 1) return centerX - (isMobile ? 110 : 240);
                        if (i === 2) return centerX - (isMobile ? 40 : 80);
                        if (i === 3) return centerX + (isMobile ? 40 : 80);
                        if (i === 4) return centerX + (isMobile ? 110 : 240);
                        if (i === 5) return centerX + (isMobile ? 180 : 400);
                        return centerX;
                    },
                    y: (i) => {
                        if (i === 0) return centerY - (isMobile ? 120 : 300);
                        if (i === 1) return centerY - (isMobile ? 70 : 180);
                        if (i === 2) return centerY - (isMobile ? 25 : 60);
                        if (i === 3) return centerY + (isMobile ? 25 : 60);
                        if (i === 4) return centerY + (isMobile ? 70 : 180);
                        if (i === 5) return centerY + (isMobile ? 120 : 300);
                        return centerY;
                    },
                    rotation: -10,
                    rotateX: 4,
                    rotateY: 10,
                    duration: 1,
                    ease: "power2.out",
                    delay: 0.3,
                });
            }

            animate();

            window.addEventListener("resize", () => {
                gsap.killTweensOf(".flip-image");
                animate();
            });
        }
    };

    var stackElement = function () {
        if ($(".stack-element").length > 0) {
            let scrollTriggerInstances = [];

            const updateTotalHeight = () => {
                const containerHeight = $(".stack-element-main").outerHeight();

                scrollTriggerInstances.forEach((instance) => instance.kill());
                scrollTriggerInstances = [];

                const elements = document.querySelectorAll(".element:not(:last-child)");

                elements.forEach((element, index) => {
                    const elementHeight = element.offsetHeight;

                    const pinTrigger = ScrollTrigger.create({
                        trigger: element,
                        scrub: 1,
                        start: "top top+=30",
                        end: `+=${containerHeight - elementHeight}`,
                        pin: true,
                        pinSpacing: false,
                        animation: gsap.to(element, {
                            scale: 0.9,
                            opacity: 0,
                        }),
                    });

                    scrollTriggerInstances.push(pinTrigger);
                });
            };

            updateTotalHeight();

            let resizeTimeout;
            window.addEventListener("resize", () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(updateTotalHeight, 150);
            });
        }
    };
    function stackElement2() {
        const container = document.querySelector(".stack-element-2");
        if (!container) return;

        gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);

        ScrollTrigger.getAll().forEach((st) => st.kill());

        ScrollTrigger.matchMedia({
            "(min-width: 992px)": () => {
                const elements = container.querySelectorAll(".element");

                let totalHeight = 0;
                elements.forEach((el, i) => {
                    if (i > 0) totalHeight += el.offsetHeight;
                });

                let tl = gsap.timeline({
                    scrollTrigger: {
                        trigger: container,
                        start: "top top",
                        end: "+=" + totalHeight,
                        scrub: true,
                        pin: true,
                        invalidateOnRefresh: true,
                    },
                });

                elements.forEach((el, i) => {
                    if (i === 0) return;
                    tl.fromTo(el, { y: "100%" }, { y: "0%", duration: el.offsetHeight / totalHeight });
                });

                const st = tl.scrollTrigger;

                if (!container._stackBound) {
                    container.addEventListener("click", (e) => {
                        const action = e.target.closest(".action");
                        if (!action) return;

                        const el = action.closest(".element");
                        const idx = Array.from(elements).indexOf(el);
                        if (idx === -1) return;

                        let nextIndex = idx < elements.length - 1 ? idx + 1 : idx - 1;

                        const progressPer = 1 / (elements.length - 1);
                        const targetProgress = progressPer * nextIndex;

                        const targetScroll = st.start + (st.end - st.start) * targetProgress;

                        gsap.to(window, {
                            duration: 0.6,
                            scrollTo: targetScroll,
                            ease: "power2.out",
                            onStart: () => (st.scrub = false),
                            onComplete: () => (st.scrub = true),
                        });
                    });

                    container._stackBound = true;
                }
            },

            "(max-width: 991px)": () => {
                const elements = container.querySelectorAll(".element");
                elements.forEach((el) => gsap.set(el, { clearProps: "all" }));
            },
        });
    }

    var scrollSmooth = () => {
        if ($("#smooth-wrapper").length > 0) {
            let smoother = ScrollSmoother.create({
                smooth: 2,
                smoothTouch: 0.1,
                effects: true,
            });
        }
    };

    var scrollEffectFade = () => {
        if ($(".effectFade").length) {
            gsap.registerPlugin(ScrollTrigger);

            document.querySelectorAll(".effectFade").forEach((el) => {
                let fromVars = { autoAlpha: 0 };
                let toVars = { autoAlpha: 1, duration: 1, ease: "power3.out" };
                let wrapper = null;
                let startPush = "top 95%";
                let delay = el.dataset.delay ? parseFloat(el.dataset.delay) : 0;
                toVars.delay = delay;

                if (el.classList.contains("fadeUp") && !el.classList.contains("no-div")) {
                    wrapper = document.createElement("div");
                    wrapper.classList.add("overflow-hidden");
                    el.parentNode.insertBefore(wrapper, el);
                    wrapper.appendChild(el);
                }

                if (el.classList.contains("no-div")) {
                    wrapper = null;
                }
                if (el.classList.contains("fadeUp")) {
                    fromVars.y = 50;
                    toVars.y = 0;
                } else if (el.classList.contains("fadeDown")) {
                    fromVars.y = -50;
                    toVars.y = 0;
                } else if (el.classList.contains("fadeLeft")) {
                    fromVars.x = -50;
                    toVars.x = 0;
                } else if (el.classList.contains("fadeRight")) {
                    fromVars.x = 50;
                    toVars.x = 0;
                } else if (el.classList.contains("fadeRotateX")) {
                    fromVars.rotationX = 45;
                    fromVars.yPercent = 100;
                    fromVars.transformOrigin = "top center -50";
                    toVars.rotationX = 0;
                    toVars.yPercent = 0;
                    toVars.transformOrigin = "top center -50";
                    toVars.duration = 1;
                    toVars.ease = "power3.out";
                    if (wrapper) {
                        wrapper.style.perspective = "400px";
                    }
                } else if (el.classList.contains("fadeZoom")) {
                    fromVars.scale = 0.8;
                    toVars.scale = 1;
                }

                if (el.classList.contains("view-visible")) {
                    startPush = "top 101%";
                }

                gsap.set(el, fromVars);

                gsap.to(el, {
                    ...toVars,
                    scrollTrigger: {
                        trigger: el,
                        start: startPush,
                        toggleActions: "play none none none",
                    },
                });
            });
        }
    };

    var loader = function () {
        if ($(".preloader").length) {
            var innerBars = document.querySelectorAll(".inner-bar");
            var increment = 0;

            function animateBars() {
                for (var i = 0; i < 2; i++) {
                    var randomWidth = Math.floor(Math.random() * 101);
                    gsap.to(innerBars[i + increment], {
                        width: randomWidth + "%",
                        duration: 0.3,
                        ease: "none",
                    });
                }

                gsap.delayedCall(0.3, function () {
                    for (var i = 0; i < 2; i++) {
                        gsap.to(innerBars[i + increment], {
                            width: "100%",
                            duration: 0.3,
                            ease: "none",
                        });
                    }

                    increment += 2;

                    if (increment < innerBars.length) {
                        animateBars();
                    } else {
                        var preloaderTL = gsap.timeline({
                            onComplete: () => {
                                $(".preloader").remove();
                                runAnimations();
                            },
                        });

                        preloaderTL.to(".preloader", {
                            "--preloader-clip": "100%",
                            duration: 0.3,
                            ease: "none",
                        });
                    }
                });
            }

            animateBars();
        } else {
            runAnimations();
        }
    };

    var mouseHover = () => {
        if ($(".main-mouse-hover").length > 0) {
            $(".main-mouse-hover").each(function () {
                const $container = $(this);
                const $mouseEl = $container.find(".tf-mouse");

                let currentX, currentY, targetX, targetY;
                let animationFrame;

                if (!$mouseEl.hasClass("mode-2")) {
                    currentX = $container.width() / 2;
                    currentY = $container.height() / 2;
                    targetX = currentX;
                    targetY = currentY;

                    $mouseEl.css({ left: currentX + "px", top: currentY + "px" });
                }

                $container.on("mouseenter", function () {
                    $mouseEl.addClass("hover");
                    if ($mouseEl.hasClass("mode-2")) {
                        $mouseEl.css({ opacity: 1 });
                    }
                });

                $container.on("mousemove", function (e) {
                    const rect = this.getBoundingClientRect();
                    targetX = e.clientX - rect.left;
                    targetY = e.clientY - rect.top;

                    if ($mouseEl.hasClass("mode-2") && currentX === null) {
                        currentX = targetX;
                        currentY = targetY;
                    }

                    if (!animationFrame) animate();
                });

                $container.on("mouseleave", function () {
                    $mouseEl.removeClass("hover");
                    if ($mouseEl.hasClass("mode-2")) {
                        $mouseEl.css({ opacity: 0 });
                    } else {
                        targetX = $container.width() / 2;
                        targetY = $container.height() / 2;
                        if (!animationFrame) animate();
                    }
                });

                function animate() {
                    currentX += (targetX - currentX) * 0.1;
                    currentY += (targetY - currentY) * 0.1;

                    $mouseEl.css({ left: currentX + "px", top: currentY + "px" });

                    if (Math.abs(targetX - currentX) > 0.5 || Math.abs(targetY - currentY) > 0.5) {
                        animationFrame = requestAnimationFrame(animate);
                    } else {
                        animationFrame = null;
                    }
                }
            });
        }
    };

    var animateBox = () => {
        if ($(".animate-box").length > 0) {
            gsap.registerPlugin(ScrollTrigger);
            gsap.fromTo(
                ".animate-box",
                { x: -400, y: -100, scale: 0.1 },
                {
                    x: 0,
                    y: 0,
                    scale: 1,
                    duration: 1.5,
                    ease: "power3.out",
                    scrollTrigger: {
                        trigger: ".animate-box",
                        start: "top 80%",
                        toggleActions: "play none none reverse",
                    },
                }
            );
        }
    };

    var serviceScroll = () => {
        const $section = $(".section-service-2");
        const $bgList = $(".bg-image-list");
        const $bg = $bgList.find(".bg-image");
        const $cards = $section.find(".wg-service-2");

        if (!$section.length || !$cards.length) return;

        let currentIndex = 0;
        const total = $cards.length;
        let isTransitioning = false;

        // Initialize state
        function setupInitialState() {
            $cards.each(function (i) {
                const $card = $(this);
                if (i === currentIndex) {
                    $card.css({
                        opacity: 1,
                        visibility: "visible",
                        "pointer-events": "auto",
                        "z-index": 5
                    });
                } else {
                    $card.css({
                        opacity: 0,
                        visibility: "hidden",
                        "pointer-events": "none",
                        "z-index": 1
                    });
                }
            });

            $bg.each(function (i) {
                if (i === currentIndex) {
                    $(this).css({ opacity: 1, visibility: "visible" });
                } else {
                    $(this).css({ opacity: 0, visibility: "hidden" });
                }
            });

            updateIndicators(currentIndex);
        }

        function updateIndicators(idx) {
            $(".service-slide-counter").text(`0${idx + 1} / 0${total}`);
            $(".service-dot").each(function () {
                const dotIdx = parseInt($(this).data("index"), 10);
                if (dotIdx === idx) {
                    $(this).addClass("active").css({
                        width: "28px",
                        background: "#38bdf8"
                    });
                } else {
                    $(this).removeClass("active").css({
                        width: "8px",
                        background: "rgba(255, 255, 255, 0.25)"
                    });
                }
            });
        }

        const goToService = (nextIndex, direction = 1) => {
            if (isTransitioning) return;
            if (nextIndex === currentIndex) return;

            isTransitioning = true;
            const $currentCard = $cards.eq(currentIndex);
            const $nextCard = $cards.eq(nextIndex);
            const $currentBg = $bg.eq(currentIndex);
            const $nextBg = $bg.eq(nextIndex);

            // Prepare next card
            $nextCard.css({
                visibility: "visible",
                "pointer-events": "auto",
                "z-index": 6
            });
            $currentCard.css({
                "pointer-events": "none",
                "z-index": 4
            });

            if ($nextBg.length) {
                $nextBg.css({ visibility: "visible" });
            }

            const xOffset = direction > 0 ? 40 : -40;

            const tl = gsap.timeline({
                onComplete: () => {
                    $currentCard.css({
                        opacity: 0,
                        visibility: "hidden",
                        "z-index": 1
                    });
                    if ($currentBg.length) {
                        $currentBg.css({ opacity: 0, visibility: "hidden" });
                    }
                    $nextCard.css({ "z-index": 5 });
                    currentIndex = nextIndex;
                    updateIndicators(currentIndex);
                    isTransitioning = false;
                }
            });

            // 1. Fade & slide out current card
            tl.to($currentCard, {
                opacity: 0,
                x: -xOffset * 0.7,
                scale: 0.97,
                duration: 0.4,
                ease: "power2.inOut"
            }, 0);

            // 2. Crossfade background
            if ($currentBg.length && $nextBg.length) {
                tl.to($currentBg, { opacity: 0, duration: 0.45, ease: "power2.inOut" }, 0);
                tl.fromTo($nextBg, { opacity: 0 }, { opacity: 1, duration: 0.55, ease: "power2.out" }, 0.05);
            }

            // 3. Fade & slide in next card
            tl.fromTo($nextCard, 
                { opacity: 0, x: xOffset, scale: 1.02 },
                { opacity: 1, x: 0, scale: 1, duration: 0.5, ease: "power2.out" },
                0.08
            );

            // 4. Subtle zoom settle on next main image
            const $nextImg = $nextCard.find(".main-image img");
            if ($nextImg.length) {
                tl.fromTo($nextImg,
                    { scale: 1.08 },
                    { scale: 1, duration: 0.7, ease: "power2.out" },
                    0.08
                );
            }

            // 5. Mini image (image-2) animation
            const $nextMini = $nextCard.find(".image-2");
            if ($nextMini.length) {
                tl.fromTo($nextMini,
                    { opacity: 0, x: 25, scale: 0.92 },
                    { opacity: 1, x: 0, scale: 1, duration: 0.6, ease: "power2.out" },
                    0.12
                );
            }
        };

        const nextService = () => {
            const nextIndex = (currentIndex + 1) % total;
            goToService(nextIndex, 1);
        };

        const prevService = () => {
            const prevIndex = (currentIndex - 1 + total) % total;
            goToService(prevIndex, -1);
        };

        setupInitialState();

        // Round circle right arrow button click handler
        $section.off("click", ".main-image .action").on("click", ".main-image .action", function (e) {
            e.preventDefault();
            e.stopPropagation();
            nextService();
        });

        // Also clicking the main image advances to next service
        $section.off("click", ".main-image .image").on("click", ".main-image .image", function (e) {
            e.preventDefault();
            e.stopPropagation();
            nextService();
        });

        // Dot indicator click handler
        $(document).off("click", ".service-dot").on("click", ".service-dot", function (e) {
            e.preventDefault();
            const targetIdx = parseInt($(this).data("index"), 10);
            if (!isNaN(targetIdx)) {
                goToService(targetIdx, targetIdx > currentIndex ? 1 : -1);
            }
        });

        // Touch swipe support
        let touchStartX = 0;
        let touchEndX = 0;
        $section.off("touchstart touchend").on("touchstart", function (e) {
            if (e.originalEvent && e.originalEvent.changedTouches) {
                touchStartX = e.originalEvent.changedTouches[0].screenX;
            }
        }).on("touchend", function (e) {
            if (e.originalEvent && e.originalEvent.changedTouches) {
                touchEndX = e.originalEvent.changedTouches[0].screenX;
                if (touchStartX - touchEndX > 50) {
                    nextService();
                } else if (touchEndX - touchStartX > 50) {
                    prevService();
                }
            }
        });

        // Expose helpers globally
        window.nextServiceSlide = nextService;
        window.prevServiceSlide = prevService;
        window.goToServiceSlide = goToService;
    };

    var runAnimations = () => {
        serviceScroll();
        stackElement();
        scrollSmooth();
        stackElement2();
        gsapA2();
        changetext();
        scrollEffectFade();
        mouseHover();
        animateBox();
        window.runAnimations = runAnimations;
        if (typeof ScrollTrigger !== "undefined") {
            ScrollTrigger.refresh();
            setTimeout(() => ScrollTrigger.refresh(), 300);
        }
    };

    $(function () {
        loader();
    });

    $(window).on("load", function () {
        const hash = window.location.hash;
        if (hash && $(hash).length) {
            setTimeout(() => {
                gsap.to(window, {
                    duration: 1,
                    scrollTo: hash,
                    ease: "power2.out",
                });
            }, 800);
        }
    });
})(jQuery);
