import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome import automation
from esphome.automation import Condition
from esphome.const import (
    CONF_THREAD,
    CONF_TLVS,
    CONF_ON_CONNECT,
    CONF_ON_DISCONNECT,
)
from esphome.core import CORE, HexInt, coroutine_with_priority
from esphome.components.esp32 import add_idf_sdkconfig_option, get_esp32_variant, const
from esphome.components.network import IPAddress
from . import wpa2_eap

AUTO_LOAD = ["network"]

NO_WIFI_VARIANTS = [const.VARIANT_ESP32H2]

wifi_ns = cg.esphome_ns.namespace("thread")
TLVS = wifi_ns.struct("TLVs")
ThreadComponent = wifi_ns.class_("ThreadComponent", cg.Component)

ThreadConnectedCondition = wifi_ns.class_("ThreadConnectedCondition", Condition)


def validate_tlvs(value):
    value = cv.string_strict(value)
    if not value:
        return value
    if len(value) < 8:
        raise cv.Invalid("TLVs must be at least 8 characters long")
    return value

def wifi_network_ap(value):
    if value is None:
        value = {}
    return WIFI_NETWORK_AP(value)

def validate_variant(_):
    if CORE.is_esp32:
        variant = get_esp32_variant()
        if variant in NO_WIFI_VARIANTS:
            raise cv.Invalid(f"{variant} does not support WiFi")

def _validate(config):
    validate_variant(config)

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(ThreadComponent),
            cv.Optional(CONF_TLVS): validate_tlvs,
        }
    ),
    _validate,
)


def thread_network(config, ap, static_ip):
    if CONF_TLVS in config:
        cg.add(ap.set_tlvs(config[CONF_TLVS]))

    return ap


@coroutine_with_priority(60.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_use_address(config[CONF_USE_ADDRESS]))

    def add_sta(ap, network):
        ip_config = network.get(CONF_MANUAL_IP, config.get(CONF_MANUAL_IP))
        cg.add(var.add_sta(wifi_network(network, ap, ip_config)))

    for network in config.get(CONF_NETWORKS, []):
        cg.with_local_variable(network[CONF_ID], TLVS(), add_sta, network)

    if CONF_THREAD in config:
        conf = config[CONF_THREAD]
        tlvs = conf.get(CONF_TLVS)
        cg.with_local_variable(
            conf[CONF_ID],
            TLVS(),
            lambda ap: cg.add(var.set_tlvs(wifi_network(conf, ap, ip_config))),
        )
        cg.add(var.set_ap_timeout(conf[CONF_AP_TIMEOUT]))
        cg.add_define("USE_WIFI_AP")
    if CORE.is_esp32 and CORE.using_esp_idf:
        add_idf_sdkconfig_option("CONFIG_ESP_WIFI_SOFTAP_SUPPORT", False)
        add_idf_sdkconfig_option("CONFIG_LWIP_DHCPS", False)

    #cg.add(var.set_reboot_timeout(config[CONF_REBOOT_TIMEOUT]))
    #cg.add(var.set_power_save_mode(config[CONF_POWER_SAVE_MODE]))
    #cg.add(var.set_fast_connect(config[CONF_FAST_CONNECT]))
    #cg.add(var.set_passive_scan(config[CONF_PASSIVE_SCAN]))

    #cg.add(var.set_enable_on_boot(config[CONF_ENABLE_ON_BOOT]))

    #if CORE.is_esp8266:
    #    cg.add_library("ESP8266WiFi", None)
    #elif CORE.is_esp32 and CORE.using_arduino:
    #    cg.add_library("WiFi", None)
    #elif CORE.is_rp2040:
    #    cg.add_library("WiFi", None)

    if CORE.is_esp32 and CORE.using_esp_idf:
        #if config[CONF_ENABLE_BTM] or config[CONF_ENABLE_RRM]:
            add_idf_sdkconfig_option("CONFIG_WPA_11KV_SUPPORT", True)
            cg.add_define("USE_WIFI_11KV_SUPPORT")
        #if config[CONF_ENABLE_BTM]:
        #    cg.add(var.set_btm(config[CONF_ENABLE_BTM]))
        #if config[CONF_ENABLE_RRM]:
        #    cg.add(var.set_rrm(config[CONF_ENABLE_RRM]))
    else
        raise cv.Invalid(f"{variant} does not support WiFi")

    cg.add_define("USE_WIFI")

    # must register before OTA safe mode check
    await cg.register_component(var, config)

    await cg.past_safe_mode()

    #if on_connect_config := config.get(CONF_ON_CONNECT):
    #    await automation.build_automation(
    #        var.get_connect_trigger(), [], on_connect_config
    #    )

    #if on_disconnect_config := config.get(CONF_ON_DISCONNECT):
    #    await automation.build_automation(
    #        var.get_disconnect_trigger(), [], on_disconnect_config
    #    )



#@automation.register_condition("wifi.enabled", WiFiEnabledCondition, cv.Schema({}))
#async def wifi_enabled_to_code(config, condition_id, template_arg, args):
#    return cg.new_Pvariable(condition_id, template_arg)


#@automation.register_action("wifi.enable", WiFiEnableAction, cv.Schema({}))
#async def wifi_enable_to_code(config, action_id, template_arg, args):
#    return cg.new_Pvariable(action_id, template_arg)


#@automation.register_action("wifi.disable", WiFiDisableAction, cv.Schema#({}))
#async def wifi_disable_to_code(config, action_id, template_arg, args):
#    return cg.new_Pvariable(action_id, template_arg)
