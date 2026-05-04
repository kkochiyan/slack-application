from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import AsyncSessionLocal
from app.services.auth_service import AuthService
from app.services.call_ws_manager import call_ws_manager

router = APIRouter(tags=["Calls"])

async def get_current_user_from_ws_token(token: str):
    async with AsyncSessionLocal() as db:
        return await AuthService.get_current_user(db, token)

@router.websocket("/ws/calls")
async def calls_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        current_user = await get_current_user_from_ws_token(token)
    except Exception as e:
        print(f'[CALL_WS] auth failed token={token}, error={e}')
        await websocket.close(code=1008)
        return

    await call_ws_manager.connect(current_user.id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            print(f'[CALL_WS] received from user={current_user.id}: {data}')

            message_type = data.get("type")
            target_user_id_raw = data.get("target_user_id")

            if not message_type or not target_user_id_raw:
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Invalid signaling payload",
                    }
                )
                continue

            try:
                target_user_id = UUID(target_user_id_raw)
            except ValueError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Invalid target_user_id",
                    }
                )
                continue

            if message_type == "call_invite":
                if call_ws_manager.is_in_call(target_user_id):
                    await websocket.send_json(
                        {
                            "type": "user_busy",
                            "target_user_id": str(target_user_id),
                        }
                    )
                    print(
                        f'[CALL_WS] user_busy: caller={current_user.id}, target={target_user_id}'
                    )
                    continue

            message = {
                "type": message_type,
                "from_user_id": str(current_user.id),
                "from_display_name": current_user.display_name,
                "channel_id": data.get("channel_id"),
                "call_id": data.get("call_id"),
                "payload": data.get("payload"),
            }

            print(
                f'[CALL_WS] forwarding type={message_type} '
                f'from={current_user.id} to={target_user_id} call_id={message.get("call_id")}'
            )

            forwarded = await call_ws_manager.send_to_user(
                target_user_id,
                message,
            )

            if not forwarded:
                if message_type == "call_accept":
                    call_ws_manager.end_call(current_user.id)
                    call_ws_manager.end_call(target_user_id)

                await websocket.send_json(
                    {
                        "type": "user_unavailable",
                        "target_user_id": str(target_user_id),
                    }
                )
                print(
                    f'[CALL_WS] user_unavailable sent back to '
                    f'user={current_user.id}, target={target_user_id}'
                )
                continue

            if message_type == "call_accept":
                call_ws_manager.start_call(current_user.id)
                call_ws_manager.start_call(target_user_id)

            if message_type in ("call_end", "call_reject"):
                call_ws_manager.end_call(current_user.id)
                call_ws_manager.end_call(target_user_id)

    except WebSocketDisconnect as e:
        print(
            f'[CALL_WS] WebSocketDisconnect user={current_user.id}, '
            f'code={getattr(e, "code", None)}'
        )
        call_ws_manager.disconnect(current_user.id, websocket)
    except Exception as e:
        print(f'[CALL_WS] unhandled exception user={current_user.id}, error={e}')
        call_ws_manager.disconnect(current_user.id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass