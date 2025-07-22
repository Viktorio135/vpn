from fastapi import APIRouter, Request


from utils.rabbitmq import RabbitMq


router = APIRouter()


@router.post("/cryptocloud/")
async def cryptocloud_postback(request: Request):
    form = await request.form()
    payload = dict(form)

    status = payload.get('status')
    invoice_id = payload.get('invoice_id')
    amount_crypto = payload.get('amount_crypto')
    currency = payload.get('currency')
    order_id = payload.get('order_id')
    token = payload.get('token')

    await RabbitMq.publish_message({
        'status': status,
        'invoice_id': invoice_id,
        'amount_crypto': amount_crypto,
        'currency': currency,
        'order_id': order_id,
        'token': token
    }, is_payment=True)

    return {'message': 'Postback received'}