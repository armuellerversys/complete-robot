function makeSlider(id, when_changed) {
    let touched = false;
    let changed = false;
    let position = 0;
    const slider = $('#' + id);
    const slider_tick = slider.find('.slider_tick')[0];

    const set_position = function(new_position) {
        // Clamp position between -200 and 200 based on your viewBox
        position = Math.round(Math.max(-100, Math.min(100, new_position)));
        slider_tick.setAttribute('cy', position);
        changed = true;
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
    slider.on('touchend', () => touched = false);

    // --- Mouse Events Fix ---
    slider.on('mousedown', event => {
        event.preventDefault(); // Prevent text selection
        touched = true; 

        // Define handlers inside mousedown to capture this slider's context
        const handleMouseMove = function(event) {
            if (touched) {
                let from_top = event.pageY - slider.offset().top;
                let relative_mouse = (from_top / slider.height()) * 200;
                set_position(relative_mouse - 100);
                event.preventDefault();
            }
        };

        const handleMouseUp = function() {
            touched = false;
            // Unbind the handlers when dragging stops
            $(document).off('mousemove', handleMouseMove);
            $(document).off('mouseup', handleMouseUp);
        };

        // Bind the document listeners specific to this drag operation
        $(document).on('mousemove', handleMouseMove);
        $(document).on('mouseup', handleMouseUp);
    });
    
    // --- Update Loops ---
    const update = function() {
        if(!touched && Math.abs(position) > 0) {
            // drift back to the middle
            let error = 0 - position;
            let change = (0.3 * error) + (Math.sign(error) * 0.5);
            set_position(position + change);
        }
    };
    setInterval(update, 50);

    const update_if_changed = function() {
        if(changed) {
            changed = false;
            // Invert the track so 'up' is positive
            when_changed(-position);
        }
    };
    setInterval(update_if_changed, 200);
}