from flask import Blueprint, request, jsonify


webhook = Blueprint(
    "webhook",
    __name__
)


@webhook.route("/palpluss", methods=["POST"])
def palpluss_callback():

    data = request.json

    print("PAYMENT CALLBACK:")
    print(data)


    # TODO:
    # verify transaction
    # update wallet


    return jsonify({
        "status":"received"
    })
