function makeSlider(id, when_changed) {
    let touched = false;
    let changed = false;
    let position = 0; // -100 (top) to +100 (bottom)
    let lastSentPosition = null;

    const slider = $('#' + id);
    const slider_tick = slider.find('.slider_tick')[0];

    const set_position = function(new_position) {
        let clamped = Math.round(Math.max(-100, Math.min(100, new_position)));
        
        // Deadzone check: Snap near-zero positions directly to 0
        if (Math.abs(clamped) < 3) {
            clamped = 0;
        }

        if (position !== clamped) {
            position = clamped;
            slider_tick.setAttribute('cy', position);
            changed = true;
        }
    };

    // --- Touch Events ---
    slider.on('touchmove', event => {
        let touch = event.targetTouches[0];
        let from_top = touch.pageY - slider.offset().top;
        let relative_touch = (from_top / slider.height()) * 200;
        set_position(relative_touch - 100);
        touched = true;
        event.preventDefault();
    });

    slider.on('touchend touchcancel', () => {
        touched = false;
    });

    // --- Mouse Events ---
    slider.on('mousedown', event => {
        event.preventDefault();
        touched = true;

        const handleMouseMove = function(e) {
            if (touched) {
                let from_top = e.pageY - slider.offset().top;
                let relative_mouse = (from_top / slider.height()) * 200;
                set_position(relative_mouse - 100);
            }
        };

        const handleMouseUp = function() {
            touched = false;
            $(document).off('mousemove', handleMouseMove);
            $(document).off('mouseup', handleMouseUp);
        };

        $(document).on('mousemove', handleMouseMove);
        $(document).on('mouseup', handleMouseUp);
    });

    // --- Auto-center / Decay Loop ---
    setInterval(() => {
        if (!touched && position !== 0) {
            // Decay position toward zero gradually
            let step = position * 0.25;
            if (Math.abs(step) < 1) {
                step = Math.sign(position) * 1;
            }
            
            let newPos = position - step;
            if ((position > 0 && newPos < 0) || (position < 0 && newPos > 0)) {
                newPos = 0;
            }
            set_position(newPos);
        }
    }, 40);

    // --- Command Dispatch Loop ---
    setInterval(() => {
        if (changed || (position === 0 && lastSentPosition !== 0)) {
            changed = false;
            lastSentPosition = position;
            // Invert track so moving up produces positive values
            when_changed(-position);
        }
    }, 100);
}