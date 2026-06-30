#include "cfg.h"
#define MAX_SPEED 100u

static uint16_t button_not_changed_counter = 0u;

void Tsk_button(void)
{
    button_not_changed_counter += MAX_SPEED;
}

bool get_button_is_pressed(void)
{
    static bool btn_last = false;
    bool btn_now;
    btn_now = (GPIO_READ() == 0u);
    return btn_now != btn_last;
}
