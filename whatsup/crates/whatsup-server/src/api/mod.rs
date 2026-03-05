pub mod auth;
pub mod files;
pub mod groups;
pub mod keys;
pub mod messages;
pub mod users;

use axum::{
    middleware,
    routing::{delete, get, patch, post, put},
    Router,
};

use crate::{middleware::auth::require_auth, state::AppState};

pub fn router(state: AppState) -> Router<AppState> {
    let auth_routes = Router::new()
        .route("/register", post(auth::register))
        .route("/login", post(auth::login))
        .route("/refresh", post(auth::refresh))
        .route("/logout", post(auth::logout))
        .route("/2fa/challenge", post(auth::two_fa_challenge))
        // Authenticated 2FA routes
        .route(
            "/2fa/setup",
            post(auth::two_fa_setup)
                .route_layer(middleware::from_fn_with_state(state.clone(), require_auth)),
        )
        .route(
            "/2fa/verify",
            post(auth::two_fa_verify)
                .route_layer(middleware::from_fn_with_state(state.clone(), require_auth)),
        )
        .route(
            "/2fa/disable",
            post(auth::two_fa_disable)
                .route_layer(middleware::from_fn_with_state(state.clone(), require_auth)),
        )
        .route(
            "/ws-ticket",
            post(auth::ws_ticket)
                .route_layer(middleware::from_fn_with_state(state.clone(), require_auth)),
        );

    let protected = Router::new()
        .route("/users/me", get(users::get_me).patch(users::update_me))
        .route("/users/search", get(users::search))
        .route("/users/:id", get(users::get_user))
        .route("/keys/bundle", put(keys::upload_bundle))
        .route("/keys/bundle/:user_id", get(keys::get_bundle))
        .route("/keys/prekeys", post(keys::replenish_prekeys))
        .route("/keys/prekey-count", get(keys::prekey_count))
        .route("/messages/send", post(messages::send_message))
        .route("/messages/:conv_id", get(messages::get_messages))
        .route("/groups", post(groups::create_group).get(groups::list_groups))
        .route("/groups/:id", get(groups::get_group))
        .route("/groups/:id/members", post(groups::add_member))
        .route("/groups/:id/members/:uid", delete(groups::remove_member))
        .route("/files/upload", post(files::upload_file))
        .route("/files/:id", get(files::download_file).delete(files::delete_file))
        .route_layer(middleware::from_fn_with_state(state.clone(), require_auth));

    Router::new()
        .nest("/api/v1/auth", auth_routes)
        .merge(protected)
}
