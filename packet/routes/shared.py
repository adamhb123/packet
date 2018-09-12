from itertools import chain
from flask import render_template, redirect

from packet import auth, app
from packet.ldap import ldap_is_eboard
from packet.member import current_packets
from packet.utils import before_request
from packet.models import MiscSignature, Packet


@app.route('/logout')
@auth.oidc_logout
def logout():
    return redirect("/")


@app.route("/packet/<freshman_username>/<packet_id>/")
@auth.oidc_auth
@before_request
def freshman_packet(freshman_username, packet_id, info=None):
    packet = Packet.query.filter_by(freshman_username=freshman_username, id=packet_id).first()

    if packet is None:
        return "Invalid packet or freshman", 404
    else:
        can_sign = False
        did_sign = False

        if app.config["REALM"] == "csh":
            can_sign = packet.is_open()

            for sig in filter(lambda sig: sig.member == info["uid"], chain(packet.upper_signatures,
                                                                           packet.misc_signatures)):
                if isinstance(sig, MiscSignature):
                    did_sign = True
                else:
                    did_sign = sig.signed

                break
        else:
            for sig in filter(lambda sig: sig.freshman_username == info["uid"], packet.fresh_signatures):
                can_sign = packet.is_open()
                did_sign = sig.signed
                break

        return render_template("packet.html", info=info, packet=packet, can_sign=can_sign, did_sign=did_sign,
                               required=packet.signatures_required(), received=packet.signatures_received(),
                               eboard=filter(lambda sig: sig.eboard, packet.upper_signatures),
                               upper=filter(lambda sig: not sig.eboard, packet.upper_signatures))


@app.route("/packets")
@auth.oidc_auth
@before_request
def packets(info=None):
    if app.config["REALM"] == "csh":
        if info["member_info"]["onfloor"]:
            if info["member_info"]["room"] is not None or ldap_is_eboard(info['user_obj']):
                open_packets = current_packets(info["uid"], False, True)
            else:
                open_packets = current_packets(info["uid"], False, False)
        else:
            open_packets = current_packets(info["uid"], False, False)
    else:
        open_packets = current_packets(info["uid"], True, info["onfloor"])

    open_packets.sort(key=lambda x: x.total_signatures, reverse=True)
    open_packets.sort(key=lambda x: x.did_sign, reverse=True)

    return render_template("active_packets.html", info=info, packets=open_packets)
