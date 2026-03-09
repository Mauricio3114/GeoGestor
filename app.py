import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user

from config import Config
from extensions import db, login_manager
from models import User, Jornada, Localizacao
from flask import send_file
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from datetime import datetime
from zoneinfo import ZoneInfo

import requests


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(senha):
            if not user.ativo:
                flash("Usuário inativo.", "danger")
                return redirect(url_for("login"))

            login_user(user)

            if user.perfil == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("gestor_dashboard"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.perfil != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("gestor_dashboard"))

    gestores = User.query.filter_by(perfil="gestor").all()
    dados_mapa = []
    agora = datetime.utcnow()

    for gestor in gestores:
        ultima_localizacao = (
            Localizacao.query
            .filter_by(usuario_id=gestor.id)
            .order_by(Localizacao.data_hora.desc())
            .first()
        )

        jornada_ativa = Jornada.query.filter_by(
            usuario_id=gestor.id,
            status="ativa"
        ).first()

        online = False
        if jornada_ativa and ultima_localizacao:
            diferenca = agora - ultima_localizacao.data_hora
            if diferenca.total_seconds() <= 300:
                online = True

        dados_mapa.append({
            "id": gestor.id,
            "nome": gestor.nome,
            "email": gestor.email,
            "ativo": gestor.ativo,
            "online": online,
            "latitude": float(ultima_localizacao.latitude) if ultima_localizacao else None,
            "longitude": float(ultima_localizacao.longitude) if ultima_localizacao else None,
            "data_hora": ultima_localizacao.data_hora.strftime('%d/%m/%Y %H:%M') if ultima_localizacao else "Sem localização",
            "cidade": ultima_localizacao.cidade if ultima_localizacao and ultima_localizacao.cidade else "Não informada",
            "estado": ultima_localizacao.estado if ultima_localizacao and ultima_localizacao.estado else "",
            "jornada": "Ativa" if jornada_ativa else "Encerrada"
        })

    return render_template(
        "admin_dashboard.html",
        gestores=gestores,
        dados_mapa=dados_mapa
    )


@app.route("/gestor/dashboard")
@login_required
def gestor_dashboard():
    ultima_localizacao = (
        Localizacao.query
        .filter_by(usuario_id=current_user.id)
        .order_by(Localizacao.data_hora.desc())
        .first()
    )

    jornada_ativa = Jornada.query.filter_by(usuario_id=current_user.id, status="ativa").first()

    return render_template(
        "gestor_dashboard.html",
        ultima_localizacao=ultima_localizacao,
        jornada_ativa=jornada_ativa
    )


@app.route("/jornada/iniciar", methods=["POST"])
@login_required
def iniciar_jornada():
    jornada_ativa = Jornada.query.filter_by(usuario_id=current_user.id, status="ativa").first()

    if jornada_ativa:
        flash("Já existe uma jornada ativa.", "warning")
        return redirect(url_for("gestor_dashboard"))

    jornada = Jornada(usuario_id=current_user.id, status="ativa")
    db.session.add(jornada)
    db.session.commit()

    flash("Jornada iniciada com sucesso.", "success")
    return redirect(url_for("gestor_dashboard"))


@app.route("/jornada/parar", methods=["POST"])
@login_required
def parar_jornada():
    jornada_ativa = Jornada.query.filter_by(usuario_id=current_user.id, status="ativa").first()

    if not jornada_ativa:
        flash("Nenhuma jornada ativa encontrada.", "warning")
        return redirect(url_for("gestor_dashboard"))

    jornada_ativa.status = "encerrada"
    jornada_ativa.fim = datetime.now(ZoneInfo("America/Fortaleza"))
    db.session.commit()

    flash("Jornada encerrada com sucesso.", "success")
    return redirect(url_for("gestor_dashboard"))


@app.route("/salvar-localizacao", methods=["POST"])
@login_required
def salvar_localizacao():
    data = request.get_json()

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not latitude or not longitude:
        return jsonify({"status": "erro", "mensagem": "Latitude e longitude obrigatórias"}), 400

    cidade = None
    estado = None

    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"

        headers = {
            "User-Agent": "GeoGestor-System"
        }

        response = requests.get(url, headers=headers)
        resultado = response.json()

        address = resultado.get("address", {})

        cidade = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )

        estado = address.get("state")

    except Exception as e:
        print("Erro ao obter cidade:", e)

    localizacao = Localizacao(
        usuario_id=current_user.id,
        latitude=str(latitude),
        longitude=str(longitude),
        cidade=cidade,
        estado=estado
    )

    db.session.add(localizacao)
    db.session.commit()

    return jsonify({"status": "ok", "mensagem": "Localização salva com sucesso"})

    db.session.add(localizacao)
    db.session.commit()

    return jsonify({"status": "ok", "mensagem": "Localização salva com sucesso"})


@app.route("/criar-admin")
def criar_admin():
    admin_existente = User.query.filter_by(email="admin@geogestor.com").first()

    if admin_existente:
        return "Admin já existe."

    admin = User(
        nome="Administrador",
        email="admin@geogestor.com",
        perfil="admin",
        ativo=True
    )
    admin.set_password("123456")

    db.session.add(admin)
    db.session.commit()

    return "Admin criado com sucesso. Email: admin@geogestor.com | Senha: 123456"


@app.route("/admin/gestores/novo", methods=["POST"])
@login_required
def criar_gestor():
    if current_user.perfil != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("gestor_dashboard"))

    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")

    if not nome or not email or not senha:
        flash("Preencha todos os campos do gestor.", "warning")
        return redirect(url_for("admin_dashboard"))

    usuario_existente = User.query.filter_by(email=email).first()
    if usuario_existente:
        flash("Já existe um usuário com esse e-mail.", "danger")
        return redirect(url_for("admin_dashboard"))

    gestor = User(
        nome=nome,
        email=email,
        perfil="gestor",
        ativo=True
    )
    gestor.set_password(senha)

    db.session.add(gestor)
    db.session.commit()

    flash("Gestor cadastrado com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/gestor/<int:gestor_id>/mapa")
@login_required
def admin_gestor_mapa(gestor_id):
    if current_user.perfil != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("gestor_dashboard"))

    gestor = User.query.filter_by(id=gestor_id, perfil="gestor").first_or_404()

    data_inicial = request.args.get("data_inicial")
    data_final = request.args.get("data_final")

    query = Localizacao.query.filter_by(usuario_id=gestor.id)

    if data_inicial:
        try:
            inicio_dt = datetime.strptime(data_inicial, "%Y-%m-%d")
            query = query.filter(Localizacao.data_hora >= inicio_dt)
        except ValueError:
            flash("Data inicial inválida.", "warning")

    if data_final:
        try:
            fim_dt = datetime.strptime(data_final, "%Y-%m-%d")
            fim_dt = fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Localizacao.data_hora <= fim_dt)
        except ValueError:
            flash("Data final inválida.", "warning")

    localizacoes = query.order_by(Localizacao.data_hora.asc()).all()

    ultima_localizacao = localizacoes[-1] if localizacoes else None

    jornada_ativa = Jornada.query.filter_by(
        usuario_id=gestor.id,
        status="ativa"
    ).first()

    online = False
    if jornada_ativa and ultima_localizacao:
        diferenca = datetime.utcnow() - ultima_localizacao.data_hora
        if diferenca.total_seconds() <= 300:
            online = True

    rota_pontos = []
    timeline = []

    for loc in localizacoes:
        try:
            lat = float(loc.latitude)
            lng = float(loc.longitude)
        except (TypeError, ValueError):
            continue

        rota_pontos.append({
            "latitude": lat,
            "longitude": lng,
            "data_hora": loc.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            "cidade": loc.cidade or "Não informada",
            "estado": loc.estado or ""
        })

        timeline.append({
            "data_hora": loc.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            "cidade": loc.cidade or "Não informada",
            "estado": loc.estado or "",
            "latitude": loc.latitude,
            "longitude": loc.longitude
        })

    return render_template(
        "admin_gestor_mapa.html",
        gestor=gestor,
        ultima_localizacao=ultima_localizacao,
        online=online,
        jornada_ativa=jornada_ativa,
        rota_pontos=rota_pontos,
        timeline=timeline,
        data_inicial=data_inicial,
        data_final=data_final
    )

@app.route("/admin/gestor/<int:gestor_id>/exportar-pdf")
@login_required
def exportar_pdf_movimentacao(gestor_id):
    if current_user.perfil != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("gestor_dashboard"))

    gestor = User.query.filter_by(id=gestor_id, perfil="gestor").first_or_404()

    data_inicial = request.args.get("data_inicial")
    data_final = request.args.get("data_final")

    query = Localizacao.query.filter_by(usuario_id=gestor.id)

    if data_inicial:
        try:
            inicio_dt = datetime.strptime(data_inicial, "%Y-%m-%d")
            query = query.filter(Localizacao.data_hora >= inicio_dt)
        except ValueError:
            pass

    if data_final:
        try:
            fim_dt = datetime.strptime(data_final, "%Y-%m-%d")
            fim_dt = fim_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Localizacao.data_hora <= fim_dt)
        except ValueError:
            pass

    localizacoes = query.order_by(Localizacao.data_hora.asc()).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "GeoGestor - Relatório de Movimentação")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Gestor: {gestor.nome}")
    y -= 20
    pdf.drawString(50, y, f"E-mail: {gestor.email}")
    y -= 20
    pdf.drawString(50, y, f"Período: {data_inicial or 'Início'} até {data_final or 'Hoje'}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Movimentações:")
    y -= 20

    pdf.setFont("Helvetica", 10)

    if not localizacoes:
        pdf.drawString(50, y, "Nenhuma movimentação encontrada para o período.")
    else:
        for loc in localizacoes:
            linha = (
                f"{loc.data_hora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"{loc.cidade or 'Não informada'}"
            )
            if loc.estado:
                linha += f"/{loc.estado}"
            linha += f" | Lat: {loc.latitude} | Lon: {loc.longitude}"

            pdf.drawString(50, y, linha[:110])
            y -= 18

            if y < 50:
                pdf.showPage()
                y = altura - 50
                pdf.setFont("Helvetica", 10)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"relatorio_movimentacao_{gestor.nome.replace(' ', '_').lower()}.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)