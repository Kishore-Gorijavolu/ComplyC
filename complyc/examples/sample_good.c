/*******************************************************************************
 *  (C) 2023 ComplyC incorporation
 *  Confidential Proprietary Information. Distribution Limited.
 *  Do Not Copy Without Prior Permission 
 * 
 *  Module Name: Clips.c
 * 
 *  Software Module : clips
 *	Author: Kishore Gorijavolu
 *	Version: V0.1
 * 
 *  Description: The clip function returns the input value "inp" clipped between
 **             the minimum value "minval" and the maximum value "maxval".
 * 
 *  TARGET    : Texas Instruments MSPM0L1305
 * 
 *  PLATFORM DEPENDENT [yes/no]: no
 * 
 *******************************************************************************
 *******************************************************************************
 *                      MISRA C Rule Violations 
 *******************************************************************************
 * Add the justification of the violated MISRA rules
 * 
 ******************************************************************************/
 

/**
 **##############################################################################
 **
 **  FUNCTION(s) : clipu
 **                clips
 **
 **  ABSTRACT
 **
 **      The clip function returns the input value "inp" clipped between
 **      the minimum value "minVal" and the maximum value "maxVal".
 **
 **      Input Parameters:
 **
 **              input = int32_t input value to be clipped
 **              minVal = low limit of clip range, uint16_t for ClipU,
 **                       int16_t for ClipS
 **              maxVal = high limit of clip range, uint16_t for ClipU,
 **                       int16_t for ClipS
 **
 **      Returns:
 **
 **              retVal = input clipped between minVal and maxVal, uint16_t for
 **                       clipu, int16_t for clips
 **
 **
 **##############################################################################
 **/
 
/******************************************************************************/
/****************************** DECLARATIONS **********************************/
/******************************************************************************/

/*-- Includes --*/
#include <stdint.h>
#include <stdbool.h>
//#include "Lookup.h"

/**
 * @brief This function clips to the min or max unsigned values provided
 *
 * This simple function simply checks if the input is larger
 * or less than the provided max and min respectively and clips
 * the input to those values if needed.
 *
 * @param inp Value to be clipped if needed
 * @param minVal Unsigned minimum to clip to
 * @param maxVal Unsigned maximum to clip to
 * @return Input value clipped to provided max and min
 * @ingroup group_lookup
 */
uint16_t clipu(int32_t inp, uint16_t minVal, uint16_t maxVal)
{
    uint16_t retVal;

    if (inp < (int32_t) minVal)
    {
    retVal = minVal;
    }
    else if (inp > (int32_t) maxVal)
    {
    retVal = maxVal;
    }
    else
    {
    retVal = (uint16_t) inp;
    }

    return (retVal);
}

/**
 * @brief This function clips to the min or max signed values provided
 *
 * This simple function simply checks if the input is larger
 * or less than the provided max and min respectively and clips
 * the input to those values if needed.
 *
 * @param inp Value to be clipped if needed
 * @param minVal Signed minimum to clip to
 * @param maxVal Signed maximum to clip to
 * @return Input value clipped to provided max and min
 * @ingroup group_lookup
 */
int16_t clips(int32_t inp, int16_t minVal, int16_t maxVal)
{
    int16_t retVal;

    if (inp < (int32_t) minVal)
    {
        retVal = minVal;
    }
    else if (inp > (int32_t) maxVal)
    {
        retVal = maxVal;
    }
    else
    {
        retVal = (int16_t) inp;
    }

    return (retVal);
}

