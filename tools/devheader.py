#!/usr/bin/env python3
#
# This file is used in order to generate header files for userspace
# drivers based on the layout json file given in argument.
# This permit to generate the following information for each mappable device:
# - address
# - size
# - IRQ list
# - GPIO couple (pin/port) list
#
# each device has its own file header (i.e. usart1.h, usb-otg-fs.h and so on),
# containing a static const structure named with the device name with
# the following pattern: <devname>_dev_infos (e.g. usart1_dev_infos).
#
# Generated headers can be included concurrently. They do not require any
# specific permission and do not host any executable content.

import sys
import os
# with collection, we keep the same device order as the json file
import json, collections
import re

if len(sys.argv) != 3:
    print("usage: ", sys.argv[0], "<outdir> <filename.json>\n");
    sys.exit(1);

# mode is C or ADA
outdir = sys.argv[1];
filename = sys.argv[2];

########################################################
# C file header and footer
########################################################

# print type:
c_header = """/*
 *
 * Copyright 2018 The wookey project team <wookey@ssi.gouv.fr>
 *   - Ryad     Benadjila
 *   - Arnauld  Michelizza
 *   - Mathieu  Renard
 *   - Philippe Thierry
 *   - Philippe Trebuchet
 *
 * This package is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published
 * the Free Software Foundation; either version 2.1 of the License, or (at
 * ur option) any later version.
 *
 * This package is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along
 * with this package; if not, write to the Free Software Foundation, Inc., 51
 * Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 *
 * This file has been generated by devheader.py from a Tataouine SDK Json layout file
 *
 */
"""

c_definition = """

#include "api/types.h"
#include "api/syscall.h"


/*
** This file defines the valid adress ranges where devices are mapped.
** This allows the kernel to check that device registration requests correct
** mapping.
**
** Of course these informations are SoC specific
** This file may be completed by a bord specific file for board devices
*/

/*!
** \\brief Structure defining the STM32 device map
**
** This table is based on doc STMicro RM0090 Reference manual memory map
** Only devices that may be registered by userspace are mapped here
**
** See #soc_devices_list
*/

struct user_driver_device_gpio_infos {
    uint8_t    port;
    uint8_t    pin;
};

struct user_driver_device_infos {
    physaddr_t addr;       /**< Device MMIO base address */
    uint32_t   size;       /**< Device MMIO mapping size */
    uint8_t    irq[4];     /**< IRQ line, when exist, or 0, max 4 irq lines per device */
    /** GPIO informations of the device (pin, port) */
    struct user_driver_device_gpio_infos gpios[4];
};


""";


c_footer= """

#endif
""";

if not os.path.exists(outdir):
    os.makedirs(outdir);


with open(filename, "r") as jsonfile:
    data = json.load(jsonfile, object_pairs_hook=collections.OrderedDict);


def generate_c():

    # structure definition
    with open(os.path.join(outdir, 'devinfo.h'), "w") as devinfofile:
            devinfofile.write(c_header);
            devinfofile.write("#ifndef DEVINFO_H_\n");
            devinfofile.write("# define DEVINFO_H_\n");
            devinfofile.write(c_definition);
            devinfofile.write("#endif/*!DEVINFO_H_*/\n");

    for device in data:
        dev = data[device];
        if dev["size"] == "0":
            # we do not generate headers for unmappable device (e.g. DMA)
            continue;
        devfilename = device + ".h";
        devheadername = device.upper() + "_H_";
        with open(os.path.join(outdir, devfilename), "w") as devfile:
            # header (license)
            devfile.write(c_header);
            # preprocessing and inclusion
            devfile.write("#ifndef %s\n" % devheadername);
            devfile.write("# define %s\n" % devheadername);
            devfile.write("\n#include \"generated/devinfo.h\"\n\n");

            # generating defines for IRQ values
            irqs = dev["irqs"];
            for index, irq in enumerate(irqs):
                if irq != 0:
                    irqvals = dev["irqs_literal"];
                    devfile.write("#define %s %d\n" % (irq, irqvals[index]));

            # global variable declaration
            devfile.write("\nstatic const struct user_driver_device_infos %s_dev_infos = {\n" % device);
            # device address
            devfile.write("    .address = %s,\n" % dev["address"]);
            # device size
            devfile.write("    .size    = %s,\n" % dev["size"]);
            # device irqs
            irqs = dev["irqs"];
            devfile.write("    .irqs[] = { ");
            devfile.write("    %s" % irqs[0]);
            for irq in irqs[1:]:
                devfile.write(", %s" % irq);
            devfile.write(" },\n");
            # device gpios
            devfile.write("    .gpios[] = {\n");
            if 'gpios' in dev:
                gpios = dev["gpios"];
                for gpio in gpios[0:]:
                    devfile.write("      { %s, %s },\n" % (gpio["port"], gpio["pin"]));
                if len(gpios) < 4:
                    for i in range(len(gpios), 4):
                        devfile.write("      { 0, 0 },\n");

            else:
                for i in [1, 2, 3, 4]:
                    devfile.write("      { 0, 0 },\n");
            devfile.write("    }\n");
            devfile.write("};\n");

            # closing preprocessing
            devfile.write(c_footer);


generate_c();
