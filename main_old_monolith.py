

from __future__ import annotations

# Entry point: use modularized Tk app
from app_tk import DistributedCommsSimulator




import math 
import os 
import random 
import time 



try :
    import tkinter as tk 
    from tkinter import ttk 

    TK_AVAILABLE =True 
except Exception :
    TK_AVAILABLE =False 
    tk =None 
    ttk =None 

from dataclasses import dataclass 
from typing import Callable ,Dict ,List ,Optional ,Tuple 






@dataclass (frozen =True )
class Node :
    name :str 
    kind :str 
    x :int 
    y :int 


@dataclass 
class MessageToken :
    """Representasi visual + state untuk sebuah pesan yang sedang bergerak."""

    msg_id :str 
    model :str 
    src :str 
    dst :str 
    payload :str 
    created_at :float 
    hop_started_at :float 
    hop_latency_ms :int 
    color :str 


    item_id :int 

    t :float =0.0 
    duration_ms :int =600 







class Metrics :
    def __init__ (self )->None :
        self .reset ()

    def reset (self )->None :
        self .total_sent =0 
        self .total_delivered =0 
        self .total_dropped =0 
        self .latencies_ms :List [float ]=[]
        self .start_time =time .time ()

    def record_latency (self ,ms :float )->None :
        self .latencies_ms .append (ms )

    @property 
    def avg_latency_ms (self )->float :
        if not self .latencies_ms :
            return 0.0 
        return sum (self .latencies_ms )/len (self .latencies_ms )

    @property 
    def throughput_per_s (self )->float :
        elapsed =max (1e-6 ,time .time ()-self .start_time )
        return self .total_delivered /elapsed 







class DistributedCommsSimulator (tk .Tk ):




    def _all_nodes (self )->Dict [str ,Node ]:
        """Gabungkan semua node dari semua view.

        Ini mencegah KeyError saat user mengganti topologi ketika token masih berjalan.
        """
        alln :Dict [str ,Node ]={}
        for nodes in getattr (self ,"_nodes_by_view",{}).values ():
            alln .update (nodes )
        alln .update (getattr (self ,"nodes",{}))
        return alln 

    def _try_get_node (self ,key :str )->Optional [Node ]:
        return getattr (self ,"nodes",{}).get (key )or self ._all_nodes ().get (key )

    def __init__ (self )->None :
        if not TK_AVAILABLE :
            raise RuntimeError ("Tkinter tidak tersedia di environment ini")

        super ().__init__ ()
        self .title ("Simulasi Model Komunikasi Terdistribusi (RR vs PubSub vs RPC)")



        self .geometry ("1100x720")
        self .minsize (900 ,620 )


        self ._base_w =1000 
        self ._base_h =520 
        self ._last_w =None 
        self ._last_h =None 

        self ._rng =random .Random ()
        self ._msg_counter =0 
        self ._active_tokens :Dict [int ,MessageToken ]={}
        self ._order_log :List [str ]=[]


        self ._metrics :Dict [str ,Metrics ]={
        "RR":Metrics (),
        "PUBSUB":Metrics (),
        "RPC":Metrics (),
        }


        self ._auto_job :Optional [str ]=None 


        self ._active_view ="ALL"


        self ._nodes_by_view :Dict [str ,Dict [str ,Node ]]={}


        self .latency_var =tk .IntVar (value =250 )
        self .loss_var =tk .IntVar (value =10 )
        self .rate_var =tk .IntVar (value =2 )
        self .auto_var =tk .BooleanVar (value =False )

        self ._build_layout ()
        self ._build_nodes ()
        self ._render_static_scene ()
        self ._refresh_ui ()


        self ._tick ()





    def _build_layout (self )->None :
        root =ttk .Frame (self )
        root .pack (fill =tk .BOTH ,expand =True )

        root .columnconfigure (0 ,weight =0 )
        root .columnconfigure (1 ,weight =1 )
        root .rowconfigure (0 ,weight =1 )


        self .left =ttk .Frame (root ,padding =8 )
        self .left .grid (row =0 ,column =0 ,sticky ="ns",padx =(0 ,6 ))

        self .right =ttk .Frame (root ,padding =8 )
        self .right .grid (row =0 ,column =1 ,sticky ="nsew")
        self .right .columnconfigure (0 ,weight =1 )
        self .right .rowconfigure (0 ,weight =1 )


        self .tabs =ttk .Notebook (self .right )
        self .tabs .grid (row =0 ,column =0 ,sticky ="nsew")

        self .main_tab =ttk .Frame (self .tabs )
        self .compare_tab =ttk .Frame (self .tabs )
        self .tabs .add (self .main_tab ,text ="Simulasi")
        self .tabs .add (self .compare_tab ,text ="Perbandingan")

        self .main_tab .columnconfigure (0 ,weight =1 )
        self .main_tab .rowconfigure (0 ,weight =1 )
        self .main_tab .rowconfigure (1 ,weight =0 )

        self .compare_tab .columnconfigure (0 ,weight =1 )
        self .compare_tab .rowconfigure (0 ,weight =1 )


        self .canvas =tk .Canvas (self .main_tab ,bg ="#0b1020",highlightthickness =0 )
        self .canvas .grid (row =0 ,column =0 ,sticky ="nsew")


        self .canvas .bind ("<Configure>",self ._on_canvas_resize )


        log_frame =ttk .Frame (self .main_tab )
        log_frame .grid (row =1 ,column =0 ,sticky ="ew",pady =(10 ,0 ))
        log_frame .columnconfigure (0 ,weight =1 )

        ttk .Label (log_frame ,text ="Order log (urutan pesan / event):").grid (
        row =0 ,column =0 ,sticky ="w"
        )

        self .log_text =tk .Text (
        log_frame ,
        height =8 ,
        wrap =tk .NONE ,
        bg ="#0a0f1e",
        fg ="#d6deff",
        insertbackground ="#d6deff",
        )
        self .log_text .grid (row =1 ,column =0 ,sticky ="ew")
        self .log_text .configure (state =tk .DISABLED )


        self .compare_text =tk .Text (
        self .compare_tab ,
        wrap =tk .WORD ,
        bg ="#0a0f1e",
        fg ="#d6deff",
        insertbackground ="#d6deff",
        )
        self .compare_text .grid (row =0 ,column =0 ,sticky ="nsew")
        self .compare_text .configure (state =tk .DISABLED )


        ttk .Label (
        self .left ,
        text ="Kontrol Simulasi",
        font =("Helvetica",14 ,"bold"),
        ).pack (anchor ="w",pady =(0 ,8 ))


        action_box =ttk .LabelFrame (self .left ,text ="Aksi")
        action_box .pack (fill =tk .X ,pady =(0 ,10 ))

        self .rr_btn =ttk .Button (action_box ,text ="Jalankan RR (Send Request)",command =self ._rr_send )
        self .rr_btn .pack (fill =tk .X ,padx =8 ,pady =4 )

        self .pub_btn =ttk .Button (
        action_box ,text ="Jalankan PubSub (Publish Event)",command =self ._pubsub_publish 
        )
        self .pub_btn .pack (fill =tk .X ,padx =8 ,pady =4 )

        self .rpc_btn =ttk .Button (action_box ,text ="Jalankan RPC (Remote Call)",command =self ._rpc_call )
        self .rpc_btn .pack (fill =tk .X ,padx =8 ,pady =4 )

        ttk .Separator (action_box ).pack (fill =tk .X ,padx =8 ,pady =6 )

        self .reset_btn =ttk .Button (action_box ,text ="Reset metrik & log",command =self ._reset )
        self .reset_btn .pack (fill =tk .X ,padx =8 ,pady =(0 ,8 ))

        sim_box =ttk .LabelFrame (self .left ,text ="Parameter Jaringan")
        sim_box .pack (fill =tk .X ,pady =(0 ,10 ))


        latency_row =ttk .Frame (sim_box )
        latency_row .pack (fill =tk .X ,padx =8 ,pady =(6 ,0 ))
        ttk .Label (latency_row ,text ="Latency per hop (ms)").pack (side =tk .LEFT )
        self .latency_value_lbl =ttk .Label (latency_row ,text =f"{int (self .latency_var .get ())} ms")
        self .latency_value_lbl .pack (side =tk .RIGHT )

        ttk .Scale (
        sim_box ,
        from_ =0 ,
        to =1500 ,
        variable =self .latency_var ,
        command =lambda _v :self ._refresh_ui (),
        ).pack (fill =tk .X ,padx =8 ,pady =(0 ,6 ))


        loss_row =ttk .Frame (sim_box )
        loss_row .pack (fill =tk .X ,padx =8 ,pady =(6 ,0 ))
        ttk .Label (loss_row ,text ="Loss per hop (%)").pack (side =tk .LEFT )
        self .loss_value_lbl =ttk .Label (loss_row ,text =f"{int (self .loss_var .get ())}%")
        self .loss_value_lbl .pack (side =tk .RIGHT )

        ttk .Scale (
        sim_box ,
        from_ =0 ,
        to =60 ,
        variable =self .loss_var ,
        command =lambda _v :self ._refresh_ui (),
        ).pack (fill =tk .X ,padx =8 ,pady =(0 ,6 ))

        pub_box =ttk .LabelFrame (self .left ,text ="PubSub (Auto)")
        pub_box .pack (fill =tk .X ,pady =(0 ,10 ))

        ttk .Checkbutton (
        pub_box ,
        text ="Auto run (publish berkala)",
        variable =self .auto_var ,
        command =self ._toggle_auto ,
        ).pack (anchor ="w",padx =8 ,pady =(6 ,4 ))

        rate_row =ttk .Frame (pub_box )
        rate_row .pack (fill =tk .X ,padx =8 ,pady =(0 ,0 ))
        ttk .Label (rate_row ,text ="Rate (event/detik)").pack (side =tk .LEFT )
        self .rate_value_lbl =ttk .Label (rate_row ,text =f"{int (self .rate_var .get ())}/s")
        self .rate_value_lbl .pack (side =tk .RIGHT )

        ttk .Scale (
        pub_box ,
        from_ =1 ,
        to =10 ,
        variable =self .rate_var ,
        command =lambda _v :self ._refresh_ui (),
        ).pack (fill =tk .X ,padx =8 ,pady =(0 ,6 ))

        met_box =ttk .LabelFrame (self .left ,text ="Metrik (Model Aktif)")
        met_box .pack (fill =tk .X ,pady =(0 ,10 ))

        self .metrics_lbl =ttk .Label (met_box ,justify =tk .LEFT )
        self .metrics_lbl .pack (anchor ="w",padx =8 ,pady =8 )

        help_box =ttk .LabelFrame (self .left ,text ="Petunjuk Singkat")
        help_box .pack (fill =tk .BOTH ,expand =True )

        help_txt =(
        "• RR: klik 'Send Request' → kanvas menampilkan topologi RR saja.\n"
        "• RPC: klik 'Remote Call' → kanvas menampilkan topologi RPC saja.\n"
        "• PubSub: klik 'Publish Event' → kanvas menampilkan topologi PubSub saja (fan-out).\n"
        "• Naikkan Loss untuk melihat drop, naikkan Latency untuk delay.\n"
        )
        ttk .Label (help_box ,text =help_txt ,justify =tk .LEFT ).pack (
        anchor ="w",padx =8 ,pady =8 
        )





    def _build_nodes (self )->None :



        self ._nodes_by_view ={
        "RR":{

        "rr_client":Node ("RR Client","client",380 ,260 ),
        "rr_server":Node ("RR Server","server",620 ,260 ),
        },
        "RPC":{

        "rpc_client":Node ("RPC Client","client",230 ,260 ),
        "rpc_cstub":Node ("Client Stub","stub",340 ,260 ),
        "rpc_runtime_c":Node ("RPC Runtime","runtime",450 ,260 ),
        "rpc_runtime_s":Node ("RPC Runtime","runtime",560 ,260 ),
        "rpc_sstub":Node ("Server Stub","stub",670 ,260 ),
        "rpc_server":Node ("RPC Server","server",780 ,260 ),
        },
        "PUBSUB":{
        "publisher":Node ("Publisher","publisher",180 ,260 ),
        "broker":Node ("Broker","broker",520 ,260 ),
        "sub1":Node ("Sub A","subscriber",860 ,170 ),
        "sub2":Node ("Sub B","subscriber",860 ,260 ),
        "sub3":Node ("Sub C","subscriber",860 ,350 ),
        },
        }


        self ._active_view =getattr (self ,"_active_view","RR")
        self .nodes =dict (self ._nodes_by_view .get (self ._active_view ,self ._nodes_by_view ["RR"]))

    def _render_static_scene (self )->None :
        self .canvas .delete ("all")

        view =getattr (self ,"_active_view","RR")


        if hasattr (self ,"_nodes_by_view")and view in self ._nodes_by_view :
            self .nodes =dict (self ._nodes_by_view [view ])


        if view =="RR":
            self ._draw_link ("rr_client","rr_server",tag ="rr_link")
        elif view =="RPC":
            self ._draw_link ("rpc_client","rpc_cstub",tag ="rpc_link")
            self ._draw_link ("rpc_cstub","rpc_runtime_c",tag ="rpc_link")
            self ._draw_link ("rpc_runtime_c","rpc_runtime_s",tag ="rpc_link")
            self ._draw_link ("rpc_runtime_s","rpc_sstub",tag ="rpc_link")
            self ._draw_link ("rpc_sstub","rpc_server",tag ="rpc_link")
        elif view =="PUBSUB":
            self ._draw_link ("publisher","broker",tag ="pub_link")
            for s in ("sub1","sub2","sub3"):
                self ._draw_link ("broker",s ,tag ="pub_link")


        for key ,node in self .nodes .items ():
            self ._draw_node (key ,node )


        self .canvas .create_text (
        20 ,
        20 ,
        anchor ="w",
        text =f"Visualisasi Sistem (topologi: {view })",
        fill ="#d6deff",
        font =("Helvetica",13 ,"bold"),
        )

    def _draw_link (self ,a :str ,b :str ,tag :str )->None :

        na =self ._try_get_node (a )
        nb =self ._try_get_node (b )
        if na is None or nb is None :
            return 
        self .canvas .create_line (
        na .x ,
        na .y ,
        nb .x ,
        nb .y ,
        fill ="#2a355c",
        width =3 ,
        capstyle =tk .ROUND ,
        tags =(tag ,),
        )

    def _draw_node (self ,key :str ,node :Node )->None :

        r =34 
        color ={
        "client":"#4FD1C5",
        "server":"#63B3ED",
        "stub":"#FDE68A",
        "runtime":"#93C5FD",
        "publisher":"#F6AD55",
        "broker":"#B794F4",
        "subscriber":"#68D391",
        }.get (node .kind ,"#CBD5E0")

        self .canvas .create_oval (
        node .x -r ,
        node .y -r ,
        node .x +r ,
        node .y +r ,
        fill =color ,
        outline ="#0a0f1e",
        width =2 ,
        tags =(f"node:{key }",),
        )
        self .canvas .create_text (
        node .x ,
        node .y ,
        text =node .name ,
        fill ="#0a0f1e",
        font =("Helvetica",11 ,"bold"),
        tags =(f"node:{key }",),
        )


        if key in ("rr_client","rr_server"):
            group ="Request-Response"
            gy =95 
        elif key in (
        "rpc_client",
        "rpc_cstub",
        "rpc_runtime_c",
        "rpc_runtime_s",
        "rpc_sstub",
        "rpc_server",
        ):
            group ="RPC"
            gy =245 
        elif key in ("publisher","broker","sub1","sub2","sub3"):
            group ="Publish-Subscribe"
            gy =405 
        else :
            return 







    def _rr_send (self )->None :



        req_id =self ._next_msg_id ("REQ")
        payload =f"GET /resource?id={self ._rng .randint (1 ,9 )}"

        start =time .time ()
        self ._log (f"RR start {req_id }: client -> server ({payload })")

        def on_req_delivered ()->None :


            server_processing_ms =self ._rng .randint (120 ,320 )

            def after_processing ()->None :
                resp_id =req_id .replace ("REQ","RESP")
                resp_payload ="200 OK"
                self ._log (f"RR server processed {req_id }, send {resp_id }: server -> client")

                def on_resp_delivered ()->None :
                    end =time .time ()
                    e2e_ms =(end -start )*1000.0 
                    self ._metrics ["RR"].record_latency (e2e_ms )
                    self ._log (f"RR done {req_id }: e2e {e2e_ms :.0f} ms")

                self ._send_hop (
                model ="RR",
                src ="rr_server",
                dst ="rr_client",
                msg_id =resp_id ,
                payload =resp_payload ,
                color ="#63B3ED",
                on_delivered =on_resp_delivered ,
                )

            self .after (server_processing_ms ,after_processing )


        self ._active_view ="RR"
        self ._render_static_scene ()

        self ._send_hop (
        model ="RR",
        src ="rr_client",
        dst ="rr_server",
        msg_id =req_id ,
        payload =payload ,
        color ="#4FD1C5",
        on_delivered =on_req_delivered ,
        )





    def _pubsub_publish (self )->None :



        event_id =self ._next_msg_id ("EVT")
        topic ="temperature"
        value =round (self ._rng .uniform (20.0 ,34.0 ),1 )
        payload =f"topic={topic }, value={value }C"

        start =time .time ()
        self ._log (f"PUB publish {event_id }: publisher -> broker ({payload })")

        def on_to_broker ()->None :
            subs =["sub1","sub2","sub3"]
            remaining ={s :True for s in subs }

            def one_done (sub_key :str ,delivered :bool )->None :
                remaining .pop (sub_key ,None )

                if not remaining :
                    e2e_ms =(time .time ()-start )*1000.0 
                    self ._metrics ["PUBSUB"].record_latency (e2e_ms )
                    self ._log (f"PUB event {event_id } finished fanout: e2e {e2e_ms :.0f} ms")

            for s in subs :
                sub_node =self ._try_get_node (s )
                sub_name =sub_node .name if sub_node is not None else s 
                fan_id =f"{event_id }->{sub_name }"

                def delivered_cb (sub_key :str =s )->None :
                    node =self ._try_get_node (sub_key )
                    name =node .name if node is not None else sub_key 
                    self ._log (f"PUB delivered {event_id } to {name }")
                    one_done (sub_key ,True )

                def dropped_cb (sub_key :str =s )->None :
                    node =self ._try_get_node (sub_key )
                    name =node .name if node is not None else sub_key 
                    self ._log (f"PUB drop {event_id } to {name }")
                    one_done (sub_key ,False )

                self ._send_hop (
                model ="PUBSUB",
                src ="broker",
                dst =s ,
                msg_id =fan_id ,
                payload =payload ,
                color ="#68D391",
                on_delivered =delivered_cb ,
                on_dropped =dropped_cb ,
                )


        self ._active_view ="PUBSUB"
        self ._render_static_scene ()

        self ._send_hop (
        model ="PUBSUB",
        src ="publisher",
        dst ="broker",
        msg_id =event_id ,
        payload =payload ,
        color ="#F6AD55",
        on_delivered =on_to_broker ,
        )


    def _rpc_call (self )->None :
        """Simulasi Remote Procedure Call (RPC): call + (server exec) + return.

        Dibedakan dari RR dengan:
        - Semantik: pemanggilan "method" remote (bukan HTTP-like request).
        - Ada kemungkinan server melempar error aplikasi (contoh: exception) meski jaringan sukses.
        - Payload return bisa OK atau ERROR.
        """

        call_id =self ._next_msg_id ("RPC")
        method =self ._rng .choice (["getUser","getBalance","createOrder","ping"])
        args =f"id={self ._rng .randint (1 ,99 )}"
        payload =f"{method }({args })"

        start =time .time ()
        self ._log (f"RPC call {call_id }: invoke {payload }")


        self ._active_view ="RPC"
        self ._render_static_scene ()

        def on_call_arrived_server ()->None :

            server_exec_ms =self ._rng .randint (150 ,520 )
            self ._log (f"RPC server executing {payload } (exec={server_exec_ms } ms)")

            def after_exec ()->None :

                app_error_p =0.15 
                is_error =self ._rng .random ()<app_error_p 
                ret_payload ="ERROR: Exception"if is_error else "OK"

                def on_return_done ()->None :
                    e2e_ms =(time .time ()-start )*1000.0 
                    self ._metrics ["RPC"].record_latency (e2e_ms )
                    status ="ERROR"if is_error else "OK"
                    self ._log (f"RPC done {call_id }: return {status } received, e2e {e2e_ms :.0f} ms")


                self ._send_hop (
                model ="RPC",
                src ="rpc_server",
                dst ="rpc_sstub",
                msg_id =f"{call_id }-RET-1",
                payload =ret_payload ,
                color ="#FCA5A5"if is_error else "#F87171",
                on_delivered =lambda :self ._send_hop (
                model ="RPC",
                src ="rpc_sstub",
                dst ="rpc_runtime_s",
                msg_id =f"{call_id }-RET-2",
                payload =ret_payload ,
                color ="#FCA5A5"if is_error else "#F87171",
                on_delivered =lambda :self ._send_hop (
                model ="RPC",
                src ="rpc_runtime_s",
                dst ="rpc_runtime_c",
                msg_id =f"{call_id }-RET-3",
                payload =ret_payload ,
                color ="#FCA5A5"if is_error else "#F87171",
                on_delivered =lambda :self ._send_hop (
                model ="RPC",
                src ="rpc_runtime_c",
                dst ="rpc_cstub",
                msg_id =f"{call_id }-RET-4",
                payload =ret_payload ,
                color ="#FCA5A5"if is_error else "#F87171",
                on_delivered =lambda :self ._send_hop (
                model ="RPC",
                src ="rpc_cstub",
                dst ="rpc_client",
                msg_id =f"{call_id }-RET-5",
                payload =ret_payload ,
                color ="#FCA5A5"if is_error else "#F87171",
                on_delivered =on_return_done ,
                ),
                ),
                ),
                ),
                )

            self .after (server_exec_ms ,after_exec )


        self ._send_hop (
        model ="RPC",
        src ="rpc_client",
        dst ="rpc_cstub",
        msg_id =f"{call_id }-CALL-1",
        payload =payload ,
        color ="#FB7185",
        on_delivered =lambda :self ._send_hop (
        model ="RPC",
        src ="rpc_cstub",
        dst ="rpc_runtime_c",
        msg_id =f"{call_id }-CALL-2",
        payload =payload ,
        color ="#FB7185",
        on_delivered =lambda :self ._send_hop (
        model ="RPC",
        src ="rpc_runtime_c",
        dst ="rpc_runtime_s",
        msg_id =f"{call_id }-CALL-3",
        payload =payload ,
        color ="#FB7185",
        on_delivered =lambda :self ._send_hop (
        model ="RPC",
        src ="rpc_runtime_s",
        dst ="rpc_sstub",
        msg_id =f"{call_id }-CALL-4",
        payload =payload ,
        color ="#FB7185",
        on_delivered =lambda :self ._send_hop (
        model ="RPC",
        src ="rpc_sstub",
        dst ="rpc_server",
        msg_id =f"{call_id }-CALL-5",
        payload =payload ,
        color ="#FB7185",
        on_delivered =on_call_arrived_server ,
        ),
        ),
        ),
        ),
        )





    def _send_hop (
    self ,
    *,
    model :str ,
    src :str ,
    dst :str ,
    msg_id :str ,
    payload :str ,
    color :str ,
    on_delivered :Optional [Callable [[],None ]]=None ,
    on_dropped :Optional [Callable [[],None ]]=None ,
    )->None :
        """Kirim pesan untuk satu hop (src->dst) dengan latency & loss."""

        latency_ms =int (self .latency_var .get ())
        loss_p =float (self .loss_var .get ())/100.0 

        self ._metrics [model ].total_sent +=1 

        src_node =self ._try_get_node (src )
        dst_node =self ._try_get_node (dst )
        src_name =src_node .name if src_node is not None else src 
        dst_name =dst_node .name if dst_node is not None else dst 
        self ._log (f"send[{model }] {msg_id }: {src_name } -> {dst_name } (lat={latency_ms }ms)")

        dropped =self ._rng .random ()<loss_p 


        item =self ._create_message_bubble (src ,color )

        token =MessageToken (
        msg_id =msg_id ,
        model =model ,
        src =src ,
        dst =dst ,
        payload =payload ,
        created_at =time .time (),
        hop_started_at =time .time (),
        hop_latency_ms =latency_ms ,
        color =color ,
        item_id =item ,
        duration_ms =max (220 ,int (0.6 *latency_ms )+350 ),
        )
        self ._active_tokens [item ]=token 


        def finish ()->None :

            if item not in self ._active_tokens :
                return 

            self ._active_tokens .pop (item ,None )
            self .canvas .delete (item )

            if dropped :
                self ._metrics [model ].total_dropped +=1 
                src_node =self ._try_get_node (src )
                dst_node =self ._try_get_node (dst )
                src_name =src_node .name if src_node is not None else src 
                dst_name =dst_node .name if dst_node is not None else dst 
                self ._log (f"drop[{model }] {msg_id }: {src_name } -> {dst_name }")
                if on_dropped is not None :
                    on_dropped ()
                self ._refresh_ui ()
                return 

            self ._metrics [model ].total_delivered +=1 
            dst_node =self ._try_get_node (dst )
            dst_name =dst_node .name if dst_node is not None else dst 
            self ._log (
            f"deliver[{model }] {msg_id }: {dst_name } received ({payload })"
            )
            if on_delivered is not None :
                on_delivered ()
            self ._refresh_ui ()

        self .after (latency_ms ,finish )

    def _create_message_bubble (self ,src :str ,color :str )->int :
        n =self ._try_get_node (src )
        if n is None :

            n =Node (src ,"unknown",30 ,30 )
        r =8 

        return self .canvas .create_oval (
        n .x -r ,
        n .y -r ,
        n .x +r ,
        n .y +r ,
        fill =color ,
        outline ="#0a0f1e",
        width =1 ,
        )





    def _tick (self )->None :
        now =time .time ()

        for item_id ,token in list (self ._active_tokens .items ()):
            src =self ._try_get_node (token .src )
            dst =self ._try_get_node (token .dst )
            if src is None or dst is None :

                continue 

            elapsed_ms =(now -token .hop_started_at )*1000.0 
            t =min (1.0 ,max (0.0 ,elapsed_ms /max (1.0 ,float (token .hop_latency_ms ))))


            eased =0.5 -0.5 *math .cos (math .pi *t )
            x =int (src .x +(dst .x -src .x )*eased )
            y =int (src .y +(dst .y -src .y )*eased )

            r =10 
            self .canvas .coords (item_id ,x -r ,y -r ,x +r ,y +r )

        self ._refresh_ui (silent =True )
        self .after (33 ,self ._tick )

    def _on_canvas_resize (self ,event )->None :
        """Scale scene saat canvas di-resize agar tidak terpotong."""

        new_w =max (1 ,int (getattr (event ,"width",1 )))
        new_h =max (1 ,int (getattr (event ,"height",1 )))


        if self ._last_w is None or self ._last_h is None :
            self ._last_w ,self ._last_h =new_w ,new_h 
            return 

        if new_w ==self ._last_w and new_h ==self ._last_h :
            return 







        if not hasattr (self ,"_base_canvas_w")or not hasattr (self ,"_base_canvas_h"):
            self ._base_canvas_w =self ._last_w 
            self ._base_canvas_h =self ._last_h 

        base_w =float (self ._base_canvas_w )
        base_h =float (self ._base_canvas_h )


        sx =new_w /base_w 
        sy =new_h /base_h 
        s =min (sx ,sy ,1.0 )




        overflow_x =new_w -base_w *s 
        overflow_y =new_h -base_h *s 
        dx =16.0 if overflow_x >160 else max (0.0 ,overflow_x /2.0 )
        dy =max (0.0 ,overflow_y /2.0 )


        if not hasattr (self ,"_base_nodes"):
            self ._base_nodes =dict (self .nodes )

        self .nodes ={
        k :Node (n .name ,n .kind ,int (n .x *s +dx ),int (n .y *s +dy ))
        for k ,n in self ._base_nodes .items ()
        }


        self ._active_tokens .clear ()


        view =getattr (self ,"_active_view","RR")
        if hasattr (self ,"_nodes_by_view")and view in self ._nodes_by_view :
            self .nodes ={
            k :Node (n .name ,n .kind ,int (n .x *s +dx ),int (n .y *s +dy ))
            for k ,n in self ._nodes_by_view [view ].items ()
            }
        else :
            self .nodes ={
            k :Node (n .name ,n .kind ,int (n .x *s +dx ),int (n .y *s +dy ))
            for k ,n in self ._base_nodes .items ()
            }

        self ._render_static_scene ()

        self ._last_w ,self ._last_h =new_w ,new_h 





    def _log (self ,line :str )->None :
        ts =time .strftime ("%H:%M:%S")
        entry =f"[{ts }] {line }"
        self ._order_log .append (entry )

        if len (self ._order_log )>300 :
            self ._order_log =self ._order_log [-300 :]

        self .log_text .configure (state =tk .NORMAL )
        self .log_text .delete ("1.0",tk .END )
        self .log_text .insert (tk .END ,"\n".join (self ._order_log )+"\n")
        self .log_text .configure (state =tk .DISABLED )
        self .log_text .see (tk .END )

    def _refresh_ui (self ,silent :bool =False )->None :
        rr =self ._metrics ["RR"]
        ps =self ._metrics ["PUBSUB"]
        rpc =self ._metrics ["RPC"]

        def success_rate (m :Metrics )->float :
            if m .total_sent <=0 :
                return 0.0 
            return 100.0 *(m .total_delivered /m .total_sent )

        text =(
        "Metrik (RR + PubSub + RPC)\n"
        f"Latency/hop: {int (self .latency_var .get ())} ms\n"
        f"Loss/hop: {int (self .loss_var .get ())}%\n"
        "\n"
        f"RR   - Sent: {rr .total_sent }, Delivered: {rr .total_delivered }, Dropped: {rr .total_dropped }"
        f"  (Success: {success_rate (rr ):.1f}%)\n"
        f"RR   - Avg latency (e2e): {rr .avg_latency_ms :.0f} ms, Throughput: {rr .throughput_per_s :.2f}/s\n"
        "\n"
        f"PS   - Sent: {ps .total_sent }, Delivered: {ps .total_delivered }, Dropped: {ps .total_dropped }"
        f"  (Success: {success_rate (ps ):.1f}%)\n"
        f"PS   - Avg latency (e2e): {ps .avg_latency_ms :.0f} ms, Throughput: {ps .throughput_per_s :.2f}/s\n"
        "\n"
        f"RPC  - Sent: {rpc .total_sent }, Delivered: {rpc .total_delivered }, Dropped: {rpc .total_dropped }"
        f"  (Success: {success_rate (rpc ):.1f}%)\n"
        f"RPC  - Avg latency (e2e): {rpc .avg_latency_ms :.0f} ms, Throughput: {rpc .throughput_per_s :.2f}/s\n"
        )
        self .metrics_lbl .configure (text =text )

        def _pad (s :str ,w :int )->str :
            return (s +" "*w )[:w ]


        headers =[
        ("Model",6 ),
        ("Sent",8 ),
        ("Deliv",8 ),
        ("Drop",8 ),
        ("Succ%",7 ),
        ("AvgE2E(ms)",12 ),
        ("Thr(/s)",9 ),
        ]

        def row (model :str ,m :Metrics ,avg_ms :float )->str :
            return "| "+" | ".join (
            [
            _pad (model ,6 ),
            _pad (str (m .total_sent ),8 ),
            _pad (str (m .total_delivered ),8 ),
            _pad (str (m .total_dropped ),8 ),
            _pad (f"{success_rate (m ):.1f}",7 ),
            _pad (f"{avg_ms :.0f}",12 ),
            _pad (f"{m .throughput_per_s :.2f}",9 ),
            ]
            )+" |\n"

        sep ="+"+"+".join (["-"*(w +2 )for _h ,w in headers ])+"+\n"
        head ="| "+" | ".join ([_pad (h ,w )for h ,w in headers ])+" |\n"

        compare =(
        "Perbandingan Model (Tabel)\n"
        "==========================\n\n"
        +sep 
        +head 
        +sep 
        +row ("RR",rr ,rr .avg_latency_ms )
        +row ("RPC",rpc ,rpc .avg_latency_ms )
        +row ("PS",ps ,ps .avg_latency_ms )
        +sep 
        +"\n"
        "Keterangan\n"
        "- Sent/Deliv/Drop dihitung per-hop.\n"
        "- Succ% = delivered / sent * 100.\n"
        "- AvgE2E adalah rata-rata latency end-to-end.\n"
        )

        self .compare_text .configure (state =tk .NORMAL )
        self .compare_text .delete ("1.0",tk .END )
        self .compare_text .insert (tk .END ,compare )
        self .compare_text .configure (state =tk .DISABLED )


        if hasattr (self ,"latency_value_lbl"):
            self .latency_value_lbl .configure (text =f"{int (self .latency_var .get ())} ms")
        if hasattr (self ,"loss_value_lbl"):
            self .loss_value_lbl .configure (text =f"{int (self .loss_var .get ())}%")
        if hasattr (self ,"rate_value_lbl"):
            self .rate_value_lbl .configure (text =f"{int (self .rate_var .get ())}/s")


        self .rr_btn .state (["!disabled"])
        self .pub_btn .state (["!disabled"])
        self .rpc_btn .state (["!disabled"])


        if not silent :
            self .update_idletasks ()





    def _on_model_change (self )->None :

        self ._refresh_ui ()

    def _toggle_auto (self )->None :
        if self ._auto_job is not None :
            try :
                self .after_cancel (self ._auto_job )
            except Exception :
                pass 
            self ._auto_job =None 

        if not self .auto_var .get ():
            return 



        def loop ()->None :
            if not self .auto_var .get ():
                return 
            self ._pubsub_publish ()
            rate =max (1 ,int (self .rate_var .get ()))
            interval_ms =int (1000 /rate )
            self ._auto_job =self .after (interval_ms ,loop )

        loop ()

    def _reset (self )->None :

        self .auto_var .set (False )
        self ._toggle_auto ()


        for item_id in list (self ._active_tokens .keys ()):
            self .canvas .delete (item_id )
        self ._active_tokens .clear ()


        for m in self ._metrics .values ():
            m .reset ()


        self ._order_log .clear ()
        self .log_text .configure (state =tk .NORMAL )
        self .log_text .delete ("1.0",tk .END )
        self .log_text .configure (state =tk .DISABLED )

        self ._refresh_ui ()





    def main() -> None:
    app = DistributedCommsSimulator()

    try:
        style = ttk.Style(app)
        for theme in ("aqua", "clam", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
    except Exception:
        pass

    app.mainloop()


if __name__ == "__main__":
    main()

