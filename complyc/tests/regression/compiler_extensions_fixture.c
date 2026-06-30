#include <stdint.h>

__attribute__((section(".main_function"))) void TIMG1_IRQHandler(void)
{
    int x = 0;
    x++;
}

__attribute__((noinline)) void Casco_TIMG1_IRQHandler(void)
{
    TIMG1_IRQHandler();
}

__weak void weak_handler(void)
{
}

__irq void irq_handler(void)
{
}

struct __attribute__((packed)) PackedType
{
    uint8_t a;
    uint16_t b;
};
