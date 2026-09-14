function makeSlider(id, when_changed) {
    let touched = false;
    let changed = false;
    let position = 0;          // -100 (top) to +100 (bottom)
    let lastSentPosition = null;

    const slider = $('#' + id);
    const slider_tick = slider.find('.slider_tick')[0];

    // Prevent Chrome/Android from interpreting the slider movement
    // as page scrolling, zooming, etc.
    slider.css('touch-action', 'none');

    const set_position = function(new_position) {
        let clamped = Math.round(
            Math.max(-100, Math.min(100, new_position))
        );

        // Deadzone around zero
        if (Math.abs(clamped) < 3) {
            clamped = 0;
        }

        if (position !== clamped) {
            position = clamped;

            // SVG coordinate system
            slider_tick.setAttribute('cy', position);

            changed = true;
        }
    };

    function updatePosition(clientY) {
        const rect = slider[0].getBoundingClientRect();

        let from_top = clientY - rect.top;

        let relative = (from_top / rect.height) * 200;

        let new_position = relative - 100;

        set_position(new_position);
    }

    // ------------------------------------------------------------
    // Pointer Events
    // Works with:
    //   - Android touch
    //   - mouse
    //   - pen
    // ------------------------------------------------------------

    slider.on('pointerdown', function(event) {
        event.preventDefault();

        touched = true;

        // Keep receiving pointer events even if the finger moves
        // outside the SVG.
        if (slider[0].setPointerCapture) {
            slider[0].setPointerCapture(event.originalEvent.pointerId);
        }

        updatePosition(event.originalEvent.clientY);
    });

    slider.on('pointermove', function(event) {
        if (!touched) {
            return;
        }

        event.preventDefault();

        updatePosition(event.originalEvent.clientY);
    });

    slider.on('pointerup pointercancel pointerleave', function(event) {
        touched = false;

        try {
            if (slider[0].releasePointerCapture) {
                slider[0].releasePointerCapture(
                    event.originalEvent.pointerId
                );
            }
        } catch (e) {
            // Ignore releasePointerCapture errors
        }
    });


    // ------------------------------------------------------------
    // Auto-center / Decay Loop
    // ------------------------------------------------------------

    setInterval(() => {

        if (!touched && position !== 0) {

            let step = position * 0.25;

            if (Math.abs(step) < 1) {
                step = Math.sign(position) * 1;
            }

            let newPos = position - step;

            if ((position > 0 && newPos < 0) ||
                (position < 0 && newPos > 0)) {
                newPos = 0;
            }

            set_position(newPos);
        }

    }, 40);


    // ------------------------------------------------------------
    // Command Dispatch Loop
    // ------------------------------------------------------------

    setInterval(() => {

        if (changed || (position === 0 && lastSentPosition !== 0)) {

            changed = false;
            lastSentPosition = position;

            // Moving slider UP produces positive values
            when_changed(-position);
        }

    }, 100);
}